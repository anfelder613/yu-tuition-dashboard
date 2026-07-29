# CLAUDE.md — YU Peer Tuition Dashboard

This file defines how Claude Code should behave on this project.
Read this before writing any code, creating any file, or making any architectural decision.

---

## Project Overview

An interactive dashboard comparing Yeshiva University's **published tuition** (undergraduate
and graduate, separately) against 5 peer institutions, using IPEDS Cost survey data.

**This is a sibling project to the PhD Completions dashboard and the Institutional Resources
(Finance) dashboard — not a continuation of either.** Separate repo, separate folder,
separate deploy. Do not import from or modify those projects. Different IPEDS survey
component (Cost, not Completions or Finance), different unit of analysis (per-student
tuition by level, not institution-wide spending or program completions). Do not attempt to
reconcile or cross-reference figures between these dashboards in the UI.

---

## The One Question This Dashboard Answers

> **"How does YU's published tuition compare to peer institutions, by level, over the last
> decade?"**

Primary measures: **published (out-of-state / private-rate) tuition** and **required fees**,
for full-time undergraduate and full-time graduate students, shown as distinct series.
IPEDS publishes these as reported dollar figures — not a derived or computed value.

If a chart, filter, or feature does not serve that question, it does not belong here.

---

## Critical Constraint — Read Before Writing Any Code

**Undergraduate and graduate tuition are never averaged, blended, or combined into a single
"institution tuition" figure.** No such number exists in IPEDS, and inventing one would be
synthetic data by another name. They are always shown as separate series.

**All six institutions are private.** There is no in-state/in-district pricing tier for any
of them. Use only the out-of-state / private-rate fields. Do not include any in-state or
in-district variable in the pipeline — they will be blank or not meaningfully comparable for
this peer set.

Required fees are reported separately from tuition in the source data. Whether they are
summed with tuition for display or shown as their own line is an **open decision** — resolve
it in the Slice 1 grill session, not by default.

---

## Stack

- **App framework:** Streamlit
- **Language:** Python
- **Database:** PostgreSQL (same pattern as the Finance dashboard's Slice 2 — CSV → Postgres
  as the authoritative store → queried from the app, not flat-file reads baked into the app)
- **Charting:** to be decided in Slice 1 grill session (e.g. Plotly, Altair, or Streamlit's
  native chart elements) — do not assume before that conversation

Do not introduce new libraries without asking first.

---

## Project Structure

```
/app             # Streamlit app entry point and pages
/db              # Postgres schema + migrations
/scripts         # Python extraction / load scripts
/data            # raw downloaded CSVs (not committed if large — confirm .gitignore)
CLAUDE.md
PRD.md
README.md
```

Keep it flat and simple. No over-engineering. This is a prototype, not a production system.

---

## Data

### Source
IPEDS Compare Institutions tool → Cost → "Application fees, tuition and required fees, food
and housing for undergraduate and graduate students" → "Tuition and required fees for
undergraduate and graduate students (institutions reporting by academic year)."

**All data must be real.** No synthetic, sampled, or placeholder data anywhere in this
project. If a value is unavailable, show it as unavailable — do not invent it.

### Academic Year Range
**Confirmed in the Slice 1 grill session:** 2015–2016 through 2024–2025 (10 academic years).
The download turned out to include AY2024-25 (one year beyond the originally-scoped
2023-24), and it is complete — all 6 UNITIDs present, no blank values. Confirmed against the
IPEDS data dictionary text bundled with each CSV export (e.g. the `year`=2024 file's
dictionary entries read "Charges to full-time undergraduate students for the full academic
year 2024-25"), which also settles the year-labeling convention: the `year` column is the
**start** year of the academic year (year=2015 → "2015-16", year=2024 → "2024-25") — not the
end year.

### Variable Names — VERIFY, DO NOT GUESS
Confirmed variables selected, from "Tuition and fees for undergraduate and graduate students
(academic year programs)":
1. Out-of-state average tuition for full-time undergraduates
2. Out-of-state required fees for full-time undergraduates
3. Out-of-state average tuition full-time graduates
4. Out-of-state required fees for full-time graduates

**Note:** this variable's location in the IPEDS category tree is not stable year to year.
In some years it sits under a standalone "Cost" top-level category; in others it's nested
under "Institutional Characteristics > Student charges." Do not assume a fixed path when
re-pulling or re-verifying — browse each year's tree fresh.

Imputation variables were **not** included (selected "No").

The actual CSV column headers, table numbers, and any year-to-year naming changes still
need to be confirmed against the downloaded data dictionaries before writing pipeline code —
do not skip this step even though the variable selection itself is now locked in.

### Institutions (hardcoded)

| Key | Name | UNITID | Control |
|---|---|---|---|
| `yu` | Yeshiva University | 197708 | Private |
| `northeastern` | Northeastern University | 167358 | Private |
| `rpi` | Rensselaer Polytechnic Institute | 194824 | Private |
| `miami` | University of Miami (FL) | 135726 | Private |
| `stevens` | Stevens Institute of Technology | 186867 | Private |
| `clarkson` | Clarkson University | 190044 | Private |

`miami` is University of Miami (Florida) — **not** Miami University (Ohio). Confirm the
UNITID resolves to the Florida school in the downloaded data, same check as the Finance
project.

### Data Shape

```json
[
  {
    "institution": "yu",
    "academicYear": "2023-24",
    "level": "undergraduate",
    "tuition": 0000,
    "requiredFees": 0000
  },
  ...
]
```

One row per institution / year / level. Tuition and required fees stay in separate columns
regardless of how they're eventually displayed.

### Data Rules
- Show real values as-is. Do not suppress, smooth, or interpolate.
- If an institution/year has no reported value, mark it explicitly as unavailable and
  render a gap — never a zero, and never a straight line through the gap.
- Dollars are **not** inflation-adjusted in v1. State this plainly in the UI.

---

## Vertical Slice Order

Work one slice at a time. Do not start the next slice until the current one is fully working
with real data. Do not build ahead speculatively.

### Slice 1 — Data Pipeline + Undergraduate/Graduate Tuition, All Institutions

Grill session first: confirm variable names, confirm fee-handling decision, confirm
Postgres schema, confirm charting library.

- Data pipeline (CSV → PostgreSQL → app query): load script reads the downloaded CSV(s),
  maps to institution/year/level, filters to the 6 UNITIDs, loads into Postgres.
- Chart(s): tuition by academic year, undergraduate and graduate shown as clearly separate
  series (not combined), all 6 institutions.
- YU visually distinct from peers.
- Institution toggle to show/hide peers.
- Year range control.

**Done when:** Chart renders with real IPEDS data for all 6 schools, both levels, YU is
visually distinct, toggle and year control work, no synthetic values anywhere, code
committed with a clear commit message referencing the slice.

### Slice 2+ — TBD

Not scoped yet. Do not begin until Slice 1 is complete and confirmed. Candidate ideas
(unconfirmed): required fees as a toggleable add-on, year-over-year growth rate view.
Resolve in a grill session before building, not by default.

---

## Skills / Workflow (per course requirements)

- **Grill with docs:** interrogate source documentation (IPEDS variable definitions, Postgres
  schema, any Streamlit/charting docs needed) before writing code for a given slice. This
  step is not optional and not skippable under deadline pressure.
- **Implement:** build the slice per the grill session's conclusions.
- **Code review:** typically folded into the implement step rather than run as a fully
  separate pass — call it out explicitly if a slice is complex enough to warrant a standalone
  review pass.

---

## UI Rules

### Language
- Never use jargon (IPEDS, UNITID, FASB) in visible UI text.
- Say "tuition," not "cost" or "price" where the two could be conflated with net price or
  cost of attendance — this dashboard is published sticker-price tuition, not what any
  student actually pays after aid.
- Institution names in full (not abbreviations) in legends and tooltips.
- Axis labels: "Academic Year" (x), "Tuition" (y), with undergraduate/graduate clearly
  distinguished in the legend.

### Readability
- The main insight must be readable in 5 seconds without explanation.
- Every chart needs a plain-English headline above it.
- Format dollars with thousands separators and a `$` (e.g. `$52,400`).

### Layout
- Single-page app (unless the grill session concludes otherwise).
- Chart takes up the majority of the screen.
- Filters accessible but not dominant.

---

## What NOT to Do

- Do not use synthetic, sample, or placeholder data — anywhere, at any stage
- Do not average or blend undergraduate and graduate tuition into one figure
- Do not include in-state/in-district variables — none of these six institutions are public
- Do not cross-reference or link to the Completions or Finance dashboards from within the UI
- Do not add authentication or login
- Do not add institutions without updating this file and the PRD first
- Do not use technical language (IPEDS, UNITID) in any visible UI text
- Do not invent or interpolate missing values
- Do not start a new slice before the current slice is working with real data
- Do not over-engineer — this is a prototype, not a production system

---

## Resolved Data Findings

Fully confirmed in the Slice 1 grill session (2026-07-28):
- All 6 UNITIDs present in every one of the 10 files, no blank values anywhere.
- The `year` column inside each CSV matches the file → year mapping below exactly.
- Column headers: the prefix before the first `.` changes over time —
  `IC{year}_AY.` for years 2015-2023, `COST1_2024.` for 2024 — matching CLAUDE.md's earlier
  warning that this variable's category-tree location isn't stable. The loader matches on
  header **suffix** (e.g. `Out-of-state average tuition for full-time undergraduates`), not a
  fixed prefix, and hard-fails if a suffix isn't found.
- IPEDS data dictionary text (bundled `.html` file per download) confirms the `year` column is
  the **start** year of the academic year it covers — e.g. the year=2024 file's dictionary
  entries read "Charges to full-time undergraduate students for the full academic year
  2024-25." This also means the download includes one more year than originally scoped — see
  Academic Year Range above.
- Miami's UNITID (135726) resolves to "University of Miami" in the downloaded data — confirmed
  Florida, not Ohio.

### File → academic year mapping (as downloaded)

`year` value is the start year of the academic year it covers (year=2015 → AY2015-16).

| Zip file | `year` value | Academic year |
|---|---|---|
| `CSV_7232026-853.zip` | 2024 | 2024-25 |
| `CSV_7232026-987.zip` | 2023 | 2023-24 |
| `CSV_7232026-378.zip` | 2022 | 2022-23 |
| `CSV_7232026-77.zip`  | 2021 | 2021-22 |
| `CSV_7232026-747.zip` | 2020 | 2020-21 |
| `CSV_7232026-580.zip` | 2019 | 2019-20 |
| `CSV_7232026-584.zip` | 2018 | 2018-19 |
| `CSV_7232026-711.zip` | 2017 | 2017-18 |
| `CSV_7232026-151.zip` | 2016 | 2016-17 |
| `CSV_7232026-383.zip` | 2015 | 2015-16 |

Filenames are opaque and do not contain the year — same pattern as the Finance project.

---

## Definition of Done (per slice)

A slice is done when:
- [ ] It renders correctly with real IPEDS data (no placeholders, no synthetic values)
- [ ] Undergraduate and graduate tuition are shown as distinct series
- [ ] Filters/toggles work correctly
- [ ] No console/runtime errors
- [ ] Code is committed with a clear commit message referencing the slice number
