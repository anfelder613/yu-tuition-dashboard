# PRD — YU Peer Tuition Dashboard

**Author:** Avigdor Felder
**Status:** Delivered — Slice 1 complete
**Repo:** https://github.com/anfelder613/yu-tuition-dashboard
**Live:** Runs locally (Streamlit + PostgreSQL — not hostable on GitHub Pages, see §13)
**Related projects:** [PhD Completions](https://github.com/anfelder613/yu-enrollment-dashboard) · [Institutional Resources](https://github.com/anfelder613/yu-institutional-resources-dashboard) — siblings, not parents

> This document describes the dashboard as built. The verification trail for every data
> claim lives in [CLAUDE.md](CLAUDE.md) → "Resolved Data Findings."

---

## 1. Background

This is the third IPEDS dashboard in the capstone series. The first asked how much doctoral
output YU produces (Completions component). The second asked how resource-intensive YU is
(Finance component). Both are institution-facing questions about what YU *does* with money
and students.

This one asks the question from the other side of the transaction: **what YU charges.**

It is a sibling to the other two, not a continuation. Different IPEDS survey component
(Cost), different unit of analysis (per-student tuition by level, not institution-wide
spending or program completions). Figures are never reconciled or cross-referenced between
dashboards in the UI.

---

## 2. The Question

> **How does YU's published tuition compare to peer institutions, by level, over the last
> decade?**

Operationalized as: **published out-of-state / private-rate tuition and required fees**, for
full-time undergraduate and full-time graduate students, by institution, by academic year,
AY2015-16 through AY2024-25.

---

## 3. Why This Question

- **It is real and reported, not derived.** IPEDS publishes these as reported dollar
  figures — no ratio, no estimation, no imputation (imputation variables were deliberately
  excluded from the download).
- **It is comparable.** All six institutions are private, so all six report the same
  out-of-state / private-rate figure. There is no in-state tier to muddy the comparison.
- **It is a Provost question.** Price positioning against peers is squarely within the
  Provost's decision space, and it is the figure prospective families actually see.
- **It completes the picture.** With spending-per-student (Finance) and completions
  (Completions) already covered, tuition is the missing third leg — while remaining a
  separate, independently defensible dashboard.

---

## 4. The Central Constraint

**Undergraduate and graduate tuition are never averaged, blended, or combined into a single
"institution tuition" figure.**

No such number exists in IPEDS. Constructing one would require weighting undergraduate and
graduate headcounts — a weighting IPEDS does not supply for this measure — and the result
would be synthetic data by another name. The two levels are always shown as distinct series.

**Secondary misread risk:** published tuition is **sticker price**. It is not net price, not
cost of attendance, and not what any student actually pays after institutional aid. The UI
says "tuition" and never "cost" or "price," because that conflation is the most likely
misreading of the entire dashboard.

---

## 5. Users

| User | Need |
|---|---|
| **Provost Botman** (primary) | Read YU's price position against peers in 5 seconds, in a meeting |
| Provost's staff | Pull a specific institution/year/level figure on request |
| Prof. Catlin (capstone advisor) | Assess analytical judgment and data honesty |

Non-technical primary user. Clarity beats sophistication at every decision point.

---

## 6. Explicit Non-Goals

This dashboard does **not**:

- Blend undergraduate and graduate tuition into one figure
- Report net price, cost of attendance, or aid-adjusted figures
- Include in-state or in-district variables — none of these six institutions are public
- Cross-reference or link to the Completions or Finance dashboards from within the UI
- Attempt to explain *why* any institution's tuition moved
- Adjust for inflation in v1
- Include authentication or access control

---

## 7. Data

| | |
|---|---|
| **Source** | IPEDS Compare Institutions tool → Cost component |
| **Path** | "Tuition and required fees for undergraduate and graduate students (institutions reporting by academic year)" |
| **Academic years** | AY2015-16 through AY2024-25 (ten years) |
| **Institutions** | YU, Northeastern, RPI, University of Miami (FL), Stevens, Clarkson |
| **Matching** | By UNITID |
| **Pipeline** | Ten per-year CSVs → `load_ipeds_tuition.py` → PostgreSQL → Streamlit queries directly |

### Variables (four, confirmed)

1. Out-of-state average tuition for full-time undergraduates
2. Out-of-state required fees for full-time undergraduates
3. Out-of-state average tuition for full-time graduates
4. Out-of-state required fees for full-time graduates

Imputation variables were **not** included (selected "No").

### Two gotchas that shaped the loader

**Year labeling.** The `year` column is the **start** year of the academic year it covers
(`year=2015` → "2015-16", `year=2024` → "2024-25") — not the end year. Confirmed against the
IPEDS data dictionary bundled with each export, e.g. the `year=2024` file reads "Charges to
full-time undergraduate students for the full academic year 2024-25."

This also revealed that the download includes **one more year than originally scoped** —
AY2024-25, complete for all six institutions.

**Unstable column-header prefixes.** The prefix before the first `.` changes across years:
`IC{year}_AY.` for 2015–2023, `COST1_2024.` for 2024. This mirrors the fact that the
variable's location in the IPEDS category tree is itself unstable — in some years it sits
under a standalone "Cost" top-level category, in others it is nested under "Institutional
Characteristics > Student charges."

**The loader therefore matches on header suffix, not a fixed prefix, and hard-fails if a
suffix is not found.** Silently skipping an unmatched column would produce a chart with
invisible holes, which is worse than a crash.

### Data completeness

All six UNITIDs are present in every one of the ten files, with no blank values anywhere.
The `year` column inside each CSV matches the file→year mapping exactly.

**Miami check:** UNITID 135726 resolves to "University of Miami" (Florida, private) in the
downloaded data — not Miami University (Ohio). Same verification as the Finance project.

**Inflation:** v1 reports nominal dollars, stated plainly in the UI.

---

## 8. Institutions

| Key | Institution | UNITID | Control |
|---|---|---|---|
| `yu` | Yeshiva University | 197708 | Private |
| `northeastern` | Northeastern University | 167358 | Private |
| `rpi` | Rensselaer Polytechnic Institute | 194824 | Private |
| `miami` | University of Miami (FL) | 135726 | Private |
| `stevens` | Stevens Institute of Technology | 186867 | Private |
| `clarkson` | Clarkson University | 190044 | Private |

The peer set is identical to the Finance dashboard's, which keeps the two comparisons
structurally parallel even though their figures are never combined.

---

## 9. Architecture

PostgreSQL is the authoritative store. The Streamlit app **queries it directly** — there are
no flat-file reads baked into the app.

```
Ten per-year IPEDS CSVs  →  load_ipeds_tuition.py  →  Postgres  →  Streamlit app
  (scripts/ipeds_source_csv/)                        (Docker, host port 55433)
```

This follows the pattern established by the Finance dashboard, with one deliberate
difference: Finance exports to static JSON at build time because it deploys as a static site.
This app is a live Python process, so it can query Postgres directly with no export step.

**Stack:** Streamlit · Python · Plotly · PostgreSQL (Docker).

**Charting decision:** Plotly, resolved in the Slice 1 grill session. Chosen over Altair and
Streamlit's native chart elements for per-trace control over dash patterns and hover
templates — both of which the undergraduate/graduate distinction and the fees toggle depend
on.

---

## 10. Delivered Scope — Slice 1

**Data pipeline + undergraduate/graduate tuition, all six institutions.** ✅ Complete.

- Load script reads the ten CSVs, maps to institution/year/level, filters to the six
  UNITIDs, validates, and loads into Postgres
- Tuition by academic year, undergraduate and graduate as clearly separate series
  (solid vs. dashed), never combined
- YU visually distinct — YU blue `#00205B` against muted peer colors
- Institution toggles to show/hide peers
- Year range control
- Required fees toggle (see §11)

---

## 11. The Fees Decision

**The open question:** required fees are reported separately from tuition in the source data.
Should they be summed with tuition for display, or shown as their own line?

**Resolved: neither by default — fees are an opt-in toggle, off by default.**

When enabled, the chart adds a **dotted** "total incl. fees" line alongside the existing
tuition line, and the hover template reports both figures. Tuition and required fees remain
separate columns in the database regardless of display.

**Why:** summing by default would silently inflate the headline number, and every quoted
figure would then be something no institution actually publishes as its tuition. Showing
fees as a permanent second line would double the number of series on an already six-line
chart. An off-by-default toggle keeps the primary read clean while making the fuller figure
one click away — and makes the distinction visible rather than hidden.

---

## 12. Resolved Questions

| Question | Priority | Resolution |
|---|---|---|
| Exact IPEDS variable names and column headers | High | ✅ Four out-of-state variables confirmed. Headers matched by suffix, not prefix — the prefix changes (`IC{year}_AY.` → `COST1_2024.`). |
| Confirmed UNITIDs, especially University of Miami FL | High | ✅ All six present in all ten files. Miami resolves to Florida. |
| Academic-year labeling convention | High | ✅ The `year` column is the **start** year. Confirmed against the bundled data dictionary. |
| Any institution/year with missing values | High | ✅ None. No blank values anywhere. |
| Should required fees be summed with tuition? | High | ✅ Opt-in toggle, off by default — see §11. |
| Charting library | Medium | ✅ Plotly — see §9. |
| Postgres schema | Medium | ✅ `institutions` + `tuition_fees`, one row per institution/year/level. |
| Inflation adjustment | Low | Deferred — out of scope for v1. |

---

## 13. Deployment

**Not publicly hosted. Runs locally.**

This dashboard **cannot be hosted on GitHub Pages.** Pages serves static files only, and this
is a Streamlit app backed by a live PostgreSQL database — it needs a running Python process
and a running database.

Publishing it would require:

1. A Python host — Streamlit Community Cloud is the natural fit and is free.
2. A managed Postgres instance reachable from that host (e.g. Supabase, Neon, or Railway),
   with `DATABASE_URL` set as a secret.

Neither is set up. The local `docker-compose.yml` Postgres is bound to `localhost:55433` and
is not reachable from outside the machine. Credentials there are local-only, non-secret, and
public-data-only.

**Alternative if hosting becomes a requirement:** export the loaded table to a static file
and read from that instead of Postgres, which would make the app deployable to Streamlit
Cloud with no database at all. That trades the "queries a real database" property for
deployability — a reasonable trade, but a deliberate one, and a PRD update.

---

## 14. Success Criteria

1. Provost Botman reads the chart and states YU's price position unprompted, in under
   5 seconds.
2. No viewer concludes that undergraduate and graduate tuition have been combined.
3. No viewer mistakes published tuition for what students actually pay.
4. Every number traces to a downloadable IPEDS file, per institution, per year, per level.
