#!/usr/bin/env python3
"""
load_ipeds_tuition.py

Loads the ten per-year IPEDS CSVs (one academic year each, AY2015-16 through
AY2024-25 -- confirmed against the IPEDS data dictionary text bundled with
each download, e.g. the `year`=2024 file covers "the full academic year
2024-25") into PostgreSQL, which is the authoritative store for the
dashboard's data.

The measures are IPEDS's reported "Out-of-state average tuition" and
"Out-of-state required fees" for full-time undergraduates and full-time
graduates. This script does NOT compute or blend anything -- it loads
IPEDS's published values as-is, tuition and fees in separate columns,
undergraduate and graduate as separate rows. See CLAUDE.md > Critical
Constraint and > Data Rules.

Pipeline:  CSV --[this script]--> Postgres --[queried directly by the app]

What it does:
  1. Reads each expected CSV (opaque filename -> academic year, per the
     confirmed map).
  2. Locates the four value columns by header SUFFIX, not a fixed prefix --
     the prefix changes year to year (IC{year}_AY. through 2023, COST1_2024.
     for 2024). Any header whose suffix doesn't match exactly is a hard error.
  3. Validates the `year` column in every row matches the expected academic
     year for that file. Any mismatch is a hard error -- we never trust the
     filename alone.
  4. Filters to the six peer UNITIDs and asserts all six are present each
     year.
  5. Asserts no blank / non-reported values (never invents or interpolates).
  6. Loads two rows per institution per year (undergraduate, graduate) into
     tuition_fees. Idempotent: the table is truncated and repopulated in a
     single transaction, so re-running is safe.
  7. Prints an institution x year summary table for a manual gap check.

Requires:  docker compose up -d   (Postgres running with db/schema.sql applied)
           pip install -r scripts/requirements.txt
Run:       python3 scripts/load_ipeds_tuition.py
Config:    DATABASE_URL env var (defaults to the local docker-compose connection).
"""

import csv
import os
import re
import sys
from pathlib import Path

import psycopg

# --- Paths -------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = REPO_ROOT / "scripts" / "ipeds_source_csv"

# --- Connection --------------------------------------------------------------
# Non-secret local default matching docker-compose.yml. Override with DATABASE_URL.
DEFAULT_DATABASE_URL = "postgresql://yu:yu_local_dev@localhost:55433/yu_tuition"
DATABASE_URL = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)

# --- Confirmed filename -> academic year mapping -----------------------------
# Verified from each CSV's `year` column. Filenames are opaque and do NOT
# contain the year. See CLAUDE.md > File -> academic year mapping.
FILE_YEAR_MAP = {
    "CSV_7232026-383.csv": 2015,
    "CSV_7232026-151.csv": 2016,
    "CSV_7232026-711.csv": 2017,
    "CSV_7232026-584.csv": 2018,
    "CSV_7232026-580.csv": 2019,
    "CSV_7232026-747.csv": 2020,
    "CSV_7232026-77.csv": 2021,
    "CSV_7232026-378.csv": 2022,
    "CSV_7232026-987.csv": 2023,
    "CSV_7232026-853.csv": 2024,
}

# --- Confirmed UNITID -> institution key -------------------------------------
# All six private. Miami is University of Miami (FL) 135726, NOT Miami OH.
# See CLAUDE.md > Institutions.
UNITID_TO_KEY = {
    "197708": "yu",
    "167358": "northeastern",
    "194824": "rpi",
    "135726": "miami",
    "186867": "stevens",
    "190044": "clarkson",
}

# Stable display order (YU first).
KEY_ORDER = ["yu", "northeastern", "rpi", "miami", "stevens", "clarkson"]

# --- Value column header suffixes --------------------------------------------
# The prefix before the first "." changes year to year (IC2015_AY, ...,
# COST1_2024) -- confirmed by inspecting the actual downloaded files. We match
# on the suffix only and hard-fail if a header doesn't appear at all.
HEADER_SUFFIXES = {
    "undergraduate": {
        "tuition": "Out-of-state average tuition for full-time undergraduates",
        "fees": "Out-of-state required fees for full-time undergraduates",
    },
    "graduate": {
        "tuition": "Out-of-state average tuition full-time graduates",
        "fees": "Out-of-state required fees for full-time graduates",
    },
}
PREFIX_PATTERN = re.compile(r"^[^.]+\.(.+)$")


def fail(msg):
    """Print an error and exit non-zero. We stop rather than guess."""
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def locate_value_columns(headers, filename):
    """Map each (level, field) to its actual column name in this file's headers."""
    suffix_to_header = {}
    for h in headers:
        m = PREFIX_PATTERN.match(h.strip())
        if m:
            suffix_to_header[m.group(1)] = h

    columns = {}
    for level, fields in HEADER_SUFFIXES.items():
        for field, suffix in fields.items():
            if suffix not in suffix_to_header:
                fail(f"{filename}: could not find a column ending in {suffix!r}. "
                     f"Headers were: {headers}")
            columns[(level, field)] = suffix_to_header[suffix]
    return columns


def read_one_csv(path, expected_year):
    """Read one per-year CSV, validate it, and return {unitid: {(level, field): value}}."""
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        columns = locate_value_columns(headers, path.name)

        values = {}
        for row in reader:
            unitid = (row.get("unitid") or "").strip()

            row_year = (row.get("year") or "").strip()
            if row_year != str(expected_year):
                fail(f"{path.name}: row for unitid {unitid} has year {row_year!r}, "
                     f"expected {expected_year}.")

            if unitid not in UNITID_TO_KEY:
                # Not one of our six peers; skip (download was already filtered,
                # but we stay defensive).
                continue

            row_values = {}
            for (level, field), col in columns.items():
                raw = (row.get(col) or "").strip()
                if raw == "":
                    fail(f"{path.name}: blank value for unitid {unitid}, "
                         f"{level} {field} (AY{expected_year}). We never invent "
                         f"or interpolate -- investigate the source file.")
                try:
                    row_values[(level, field)] = int(raw)
                except ValueError:
                    fail(f"{path.name}: non-numeric value {raw!r} for unitid {unitid}, "
                         f"{level} {field} (AY{expected_year}).")
            values[unitid] = row_values

        return values


def read_all_records():
    """Read + validate every CSV, returning (records, grid).

    records: list of (institution_key, academic_year, level, tuition_usd, fees_usd)
    grid: grid[key][year][level] = tuition_usd, for the summary table and gap check.
    """
    if not SOURCE_DIR.is_dir():
        fail(f"Source directory not found: {SOURCE_DIR}")

    records = []
    grid = {key: {} for key in KEY_ORDER}

    for filename, year in sorted(FILE_YEAR_MAP.items(), key=lambda kv: kv[1]):
        path = SOURCE_DIR / filename
        if not path.is_file():
            fail(f"Expected source file missing: {path}")

        values = read_one_csv(path, year)

        missing = [uid for uid in UNITID_TO_KEY if uid not in values]
        if missing:
            missing_keys = ", ".join(UNITID_TO_KEY[u] for u in missing)
            fail(f"{filename} (AY{year}): missing UNITIDs for {missing_keys}. "
                 f"We never fabricate -- fix the download.")

        for unitid, row_values in values.items():
            key = UNITID_TO_KEY[unitid]
            grid[key].setdefault(year, {})
            for level in HEADER_SUFFIXES:
                tuition = row_values[(level, "tuition")]
                fees = row_values[(level, "fees")]
                records.append((key, year, level, tuition, fees))
                grid[key][year][level] = tuition

    return records, grid


def load_into_postgres(records):
    """Idempotently replace tuition_fees with `records`.

    Truncate + insert inside one transaction so the table is never left partial
    and re-running the script produces the same end state. The FK to institutions
    (seeded by db/schema.sql) rejects any key that isn't one of our six schools.
    """
    try:
        conn = psycopg.connect(DATABASE_URL)
    except psycopg.OperationalError as e:
        fail(f"Could not connect to Postgres at {DATABASE_URL!r}.\n"
             f"Is the database up?  Try:  docker compose up -d\n"
             f"Underlying error: {e}")

    with conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM institutions;")
            (n_inst,) = cur.fetchone()
            if n_inst != len(KEY_ORDER):
                fail(f"Expected {len(KEY_ORDER)} seeded institutions but found {n_inst}. "
                     f"Recreate the DB:  docker compose down -v && docker compose up -d")

            cur.execute("TRUNCATE tuition_fees;")
            cur.executemany(
                "INSERT INTO tuition_fees "
                "(institution_key, academic_year, level, tuition_usd, fees_usd) "
                "VALUES (%s, %s, %s, %s, %s);",
                records,
            )
    conn.close()


def print_summary(grid):
    """Print an institution x year table of undergraduate tuition (a spot check)."""
    years = list(range(2015, 2025))
    name_w = max(len(k) for k in KEY_ORDER)

    header = "institution".ljust(name_w) + "".join(f"{y:>9}" for y in years)
    print("Undergraduate out-of-state tuition (spot check) -- dollars, by academic year")
    print(header)
    print("-" * len(header))
    for key in KEY_ORDER:
        row = key.ljust(name_w)
        for y in years:
            v = grid[key].get(y, {}).get("undergraduate")
            row += f"{'—' if v is None else format(v, ','):>9}"
        print(row)
    print("-" * len(header))
    print("(— would indicate a missing value; none expected)")


def main():
    records, grid = read_all_records()
    load_into_postgres(records)
    print_summary(grid)
    print(f"\nLoaded {len(records)} rows into tuition_fees "
          f"at {DATABASE_URL.rsplit('@', 1)[-1]}")


if __name__ == "__main__":
    main()
