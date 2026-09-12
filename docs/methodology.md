# Methodology

Translation of the principles stated in the original brief into concrete,
checkable code behaviour — so they stay technical guarantees, not just
stated intentions.

| Principle (brief) | Translation in the code |
|---|---|
| Measured outcome indicators over declarative data/GDP aggregates | Filter applied upstream, at indicator-selection time (`config/indicators/`) — not something the pipeline can check automatically. |
| Never hide data gaps | `validate.py::coverage_summary` explicitly computes, per indicator and per entity, years covered, internal gaps (`n_missing_within_span`), and entities with no data at all. Published in `reports/coverage_report.md`, not just a log line. |
| Weighting is a moral judgement, explicit and user-adjustable | Out of backend scope: the frontend (slider-based weighting) owns this requirement. The backend just exposes `higher_is_better` per indicator so the frontend can orient the composite calculation. |
| Never a composite on "low" reliability without a visible warning | `Indicator.reliability` + `reliability_criteria` (mandatory justification, >=15 chars for `low`) are exposed in `catalog.json` — it's the frontend's job to display them as a warning at composite-calculation time. |
| "Todd" mode = metrics Todd actually used in his books | A `todd_core: bool` flag on each indicator, not a separate architecture. The frontend filters `catalog.json` on that field. |
| Traceability of inter-source duplicates | `merge.py` logs every arbitration (retained source vs. discarded sources) in `{indicator}.provenance.json` whenever several sources cover the same (entity, year). |
| Border changes (USSR, Czechoslovakia...) | `config/entities.yaml` + `EntityRegistry` — see `docs/architecture.md`. Explicitly tested in `tests/test_entity_resolution.py` and `tests/test_pipeline_integration.py`. |
| Measured, hard-to-fake data over easily-revised official aggregates | Directly stress-tested by a live-network audit that found OWID has no standalone "USSR" entity anywhere in its mortality data — the project's own principle applied to itself. Resolved: see "On the USSR tracer" below. |

## On the USSR tracer

The brief's founding example — Todd predicting the USSR's collapse from
rising Soviet infant mortality — turned out to be harder to represent than
expected. A live-network audit, and a follow-up direct check against
OWID's live API (fetching the actual entity lists for both the
`infant-mortality` indicator and OWID's deepest long-run child-mortality
series, 1751-2024), confirmed: **no OWID mortality dataset checked carries
a standalone "USSR" entity at all.** Gapminder and UN IGME, the two
underlying data providers, attach historical values directly to each
modern successor country's own code instead of preserving defunct
political unions as their own series.

Practical consequence: "Russia" (code RUS) already carries a continuous
series through the Soviet period — there was never a second, distinct
dataset to "recover" by trying more OWID slugs.

Decision (made in conversation, not unilaterally): rather than fabricate a
separate "ussr" data series that would just duplicate Russia's numbers
under a different label, each of the 15 former Soviet republics shows one
continuous series across 1991. The `formerly_part_of` field on `Entity`
(see `src/schema/entity.py`) flags the pre-1991 portion with an explicit
warning, so the frontend can surface it without the backend having to
choose between hiding the ambiguity or inventing data. The `ussr` entity
itself is kept in `entities.yaml` for reference and in case a future
source (e.g. HMD) does carry a genuine standalone series.

## On `todd_core`

The 3 pilot indicators (`infant_mortality`, `life_expectancy`,
`homicide_rate`) are all marked `todd_core: true`: strict mortality
indicators, consistent with the brief's founding example (Soviet infant
mortality). When you send the precise list, some "Extra" indicators
(measured obesity, tooth decay, net migration...) will likely be
`todd_core: false` — a content decision, not an architectural one, so
nothing needs to change in the code for that.
