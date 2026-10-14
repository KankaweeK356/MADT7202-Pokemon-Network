# Data

## `raw/decklists_snapshot.csv`

Frozen snapshot used in the submitted analysis.

Columns:
- `deck_id` — anonymous sequential deck ID; no player identity is stored
- `tournament_id` — Limitless tournament ID
- `tournament_date` — tournament date/time
- `archetype` — deck archetype classification returned by Limitless
- `card` — card name
- `category` — Pokemon / Trainer / Energy
- `copies` — number of copies in that 60-card deck

Dataset size:
- 584 valid decklists
- 14,744 card-line rows

## `raw/decklists_summary.csv`

One row per anonymous deck, used for quality checks.

## `raw/tournaments.csv`

Three Pumpkaweekly tournaments used in the study.

## `raw/source_audit.csv`

Reproducibility audit with the public tournament page and API endpoint for each event.

## Privacy / data minimization

The original public API response includes player identifiers. They are not needed for this business question,
so the frozen dataset committed to the repository removes them and assigns anonymous deck IDs.

## `processed/`

Derived data used to reproduce the submitted findings:
- raw graph edges
- business-filtered analysis edges
- node metrics
- display edges
- robustness results
- A4 findings table
