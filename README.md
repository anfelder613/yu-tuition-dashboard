# YU Peer Tuition Dashboard

> **How does YU's published tuition compare to peer institutions, by level, over the last decade?**

An interactive dashboard comparing Yeshiva University's published tuition — undergraduate
and graduate, kept strictly separate — against five private peer institutions, academic
years 2015–16 through 2024–25.

**Live:** Runs locally (Streamlit + PostgreSQL — see [Running it](#running-it))
**Status:** Slice 1 complete
**Stack:** Streamlit · Python · Plotly · PostgreSQL

---

## Scope — read this first

This is **published sticker-price tuition** — not net price, not cost of attendance, and not
what any student actually pays after aid. The UI says "tuition," never "cost" or "price,"
precisely because that conflation is the most likely misread.

**Undergraduate and graduate tuition are never averaged, blended, or combined** into a single
"institution tuition" figure. No such number exists in IPEDS, and inventing one would be
synthetic data by another name. They are always shown as distinct series.

All six institutions are private, so there is no in-state/in-district pricing tier. Only the
out-of-state / private-rate fields are used. Dollars are nominal (not inflation-adjusted).

## What it shows

- **Tuition by academic year** — all six institutions, AY2015-16 through AY2024-25.
- **Undergraduate vs. graduate** — distinct series (solid vs. dashed), never combined.
- **YU visually distinct** — YU blue (`#00205B`) against muted peer colors.
- **Required fees toggle** — off by default. When enabled, adds tuition + required fees as a
  dotted line alongside the tuition line, so fees never silently inflate the headline figure.
- **Institution toggles** and a **year range control**.

## The measure

Four IPEDS variables from the Cost survey component, "Tuition and fees for undergraduate and
graduate students (academic year programs)":

1. Out-of-state average tuition for full-time undergraduates
2. Out-of-state required fees for full-time undergraduates
3. Out-of-state average tuition for full-time graduates
4. Out-of-state required fees for full-time graduates

Tuition and required fees are stored in separate columns regardless of how they are displayed.
Imputation variables were deliberately not included.

**Year-labeling convention:** the `year` column in each CSV is the **start** year of the
academic year (`year=2024` → "2024-25"), confirmed against the IPEDS data dictionary bundled
with each export.

**Column-header instability:** the prefix before the first `.` changes over time —
`IC{year}_AY.` for 2015–2023, `COST1_2024.` for 2024. The loader matches on header **suffix**,
not a fixed prefix, and hard-fails if a suffix isn't found. This variable's location in the
IPEDS category tree is likewise not stable year to year.

See [CLAUDE.md](CLAUDE.md) → "Resolved Data Findings" for the full verification trail and the
file→academic-year mapping.

## Institutions

| Institution | UNITID | Control |
|---|---|---|
| Yeshiva University | 197708 | Private |
| Northeastern University | 167358 | Private |
| Rensselaer Polytechnic Institute | 194824 | Private |
| University of Miami (Florida) | 135726 | Private |
| Stevens Institute of Technology | 186867 | Private |
| Clarkson University | 190044 | Private |

`miami` is University of Miami (**Florida**) — not Miami University (Ohio). Confirmed against
the institution name in the downloaded data.

## Data pipeline

PostgreSQL is the authoritative store. The Streamlit app queries it directly — there are no
flat-file reads baked into the app.

```
Ten per-year IPEDS CSVs  →  load_ipeds_tuition.py  →  Postgres  →  Streamlit app
  (scripts/ipeds_source_csv/)                        (Docker)
```

### One-time setup

```bash
docker compose up -d                        # start Postgres (schema auto-applied on first run)
pip install -r scripts/requirements.txt     # loader dependencies
pip install -r app/requirements.txt         # app dependencies
```

Postgres runs in Docker on **host port 55433**. Credentials are local-only, non-secret, and
public-data-only — see `docker-compose.yml`. Both the loader and the app connect via
`DATABASE_URL`, defaulting to that local instance.

### Load the data

```bash
python3 scripts/load_ipeds_tuition.py       # CSV → validate → load Postgres (idempotent)
```

To reset the database entirely: `docker compose down -v && docker compose up -d`, then re-run
the loader.

## Running it

```bash
streamlit run app/app.py     # http://localhost:8501
```

Requires the database to be up and loaded first — see [Data pipeline](#data-pipeline).

> **Note:** this dashboard cannot be hosted on GitHub Pages. Pages serves static files only,
> and this is a Streamlit app backed by a live PostgreSQL database. Hosting it publicly would
> require a Python host (e.g. Streamlit Community Cloud) plus a managed Postgres instance.

## Data integrity

- All data is real IPEDS data. No synthetic, sampled, or placeholder values anywhere.
- All six institutions are present in all ten years, with no blank values.
- Values are shown as-is: never suppressed, smoothed, or interpolated.

## Repo layout

```
/app             # Streamlit app
/db              # Postgres schema
/scripts         # Python loader, and the source CSVs
```

## Related projects

Sibling capstone dashboards, each a separate repo answering a separate question from a
different IPEDS survey component:

- [YU PhD Completions Dashboard](https://github.com/anfelder613/yu-enrollment-dashboard) — Completions component
- [YU Institutional Resources Dashboard](https://github.com/anfelder613/yu-institutional-resources-dashboard) — Finance component
- [YU Institutional Data Dashboard](https://github.com/anfelder613/university-dashboard) — synthetic-data prototype

These are siblings, not continuations. Figures are never reconciled or cross-referenced
between dashboards.
