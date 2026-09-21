# catalog/curated/ — the curated tier (L0-L2)

Small hand-entered tables, one citation per point, committed in git and
reviewed like code. This directory implements the `curated` source type
decided in `docs/adr/0007-source-of-record-and-witnesses.md` and wired as
the canonical tier of the Todd board by
`docs/adr/0008-todd-board-canonical-layer.md`.

## Why this tier exists

The Todd method reads signals that harmonized (L3) sources smooth away by
design — and some of those signals live in official or scholarly series
that no machine-readable collector redistributes today. The curated tier
is the honest answer to that gap: enter the point, cite the point, and
make every entry individually reviewable in a pull request. It is the
opposite of scraping-and-stitching: a bounded, enumerable, auditable set.

## The curation gate (mandatory, ADR-0007 condition 3)

A point may enter a curated table only if **all three** hold:

1. **a `todd_ref` demands it** — the claim (from Todd's work or the
   project's brief) that the data must carry;
2. **the distortion is demonstrated** — the divergence vs the
   collector/harmonized layer is documented (not assumed);
3. **a citable source exists** — enforced mechanically: the connector
   (`src/connectors/curated.py`) rejects any row with an empty
   `citation` column.

If a point fails any condition, it does not enter — the gap stays
visible in the coverage report instead.

## File format

One CSV per series, named exactly as the `source_ref` used in
`config/indicators/*.yaml` (e.g. `ussr_infant_mortality_official.csv`):

    entity_id,year,value,citation,definition_note

- `entity_id` — OUR canonical id from `config/entities.yaml` (resolution
  happens by exact id; a typo surfaces in `{indicator}.unresolved.json`).
- `value` — in the indicator's canonical unit; **a gap is an absent row**,
  never an empty cell (we only enter points we can cite).
- duplicate `(entity_id, year)` rows are rejected by the parser: the
  curated tier must be arbitration-free by construction.
- `definition_note` carries the comparability caveat that travels to the
  dist next to the value (e.g. the Soviet live-birth definition).

## Current series

### `ussr_infant_mortality_official.csv` — the founding tracer

The official Soviet infant-mortality series (per-1,000 live births,
Soviet definition), 1970-1990, 21 points. This is the series at the
heart of `docs/the-measurement-problem.md` §1: the rise 22.9‰ (1971) →
peak 31.4‰ (1976) that UN IGME re-models into a 21.9‰ plateau.

**Gate check for this series:**

- (a) `todd_ref`: THE founding claim — Todd read this series *as
  published* (plus the 1976+ blackout itself) as a hard signal of
  systemic decomposition when writing *La Chute finale* (1976).
- (b) distortion demonstrated: IGME family (OWID `infant-mortality`) shows
  a flat 21.9‰ plateau for 1974-1978 where the official series shows
  27.9 → 30.6‰; documented in the-measurement-problem.md §1, verified
  during this project's live audits.
- (c) citable sources: see the per-row `citation` column.

**Provenance and cross-checks (all verified during this project's
audits, September 2026):**

- Primary compilation: the Kalabekov-style compilation of TsSU/
  Goskomstat yearbook series (su90.ru/death.html, tables [3]/[7]) — the
  "as-published family" for 1970-1974, the retrospective series (released
  late 1980s) for 1975-1990.
- Institutional carrier for 1974: **UN Demographic Yearbook 1978, Table
  15** — 125,908 infant deaths, footnote 33 spelling out the Soviet
  live-birth definition, blank cells from 1975 on (the blackout, preserved
  by the collector). Note the 27.9 (official series) vs 27.7 (DYB) nuance
  for 1974: the DYB republishes the death *count* as reported but
  recomputes the *rate* on its own births denominator — a mini-lesson in
  reading collectors carefully, recorded on the 1974 row itself.
- Arithmetic cross-check: republic-level data (IMR + births by republic,
  Narkhoz *Za 70 let* 1987) re-aggregated as
  Σ(deaths)/Σ(births) reproduces the official union figures within
  rounding — 24.66 vs 24.7 (1970), 27.26 vs 27.3 (1980), and matching
  1985/1986 points. Artifacts: `scripts/` analysis from the September
  2026 session.
- Literature anchors: Davis & Feshbach (1980, Series P-95) for the
  as-published 1970s series; Kingkade & Arriaga (1997) for the
  retrospective series; the peak 31.4‰ (1976) matches the value quoted
  in the project's founding analysis.

**Deliberately NOT done here:** no attempt to convert the series to the
WHO live-birth definition (that is an L2 scholarly reconstruction —
Anderson & Silver, Andreev-Darski-Kharkova — a separate curated series
if ever needed, with its own citations); no interpolation of anything;
the 1976-87 publication blackout is carried per-row in
`definition_note` rather than papered over.

## The marker series (v15) — the tier's second family

The markers are a different SHAPE from the founding series: one point
per country, the point's year and value BOTH the event year, the
citation the statute or the scholarly dating. The gate's condition (b)
reads differently here: for the founding series the demonstrated
distortion was a collector that stopped too early; for the markers it
is the ABSENCE of any machine-readable door at all (probed live
2026-09-20: OWID returns 404 on every candidate slug for both metrics,
and no collector prints statutes — the probe record lives in the v15
worklog and config/sources.yaml's curated notes).

### `same_sex_marriage_legalization.csv` — the 'religion zero' marker

33 countries, 2001-2025. The year each country's FIRST NATIONAL
same-sex marriage law took effect (a statute's entry into force, not
its signature; a nationwide court ruling where the statute never
preceded one — Obergefell 2015, Colombia 2016, Austria 2019's
court-ordered effective date; a referendum's year where the people
voted first — Ireland 2015).

**Gate check:**
- (a) todd_ref: La Défaite de l'Occident (2024), 13 citations — the
  'religion zero' chain (2015 -> Trump -> Ukraine war) reads from
  these very dates; Ireland's referendum and Obergefell both 2015,
  the hinge.
- (b) distortion = absence: no machine-readable door (probed live).
- (c) citations: per-row, the statute/ruling with its effective date
  (the consensus dating of the Pew Research marriage-equality
  timeline, cross-checked against the legislative record — Légifrance
  for the loi 2013-404, BOE for Ley 13/2005, the Federal Register of
  Legislation for Australia's 2017 act, etc.).

**Deliberately NOT the marker:** the registered-partnership history
(Denmark 1989, the world's first) and sub-national firsts
(Massachusetts 2004, Mexico City 2010) ride in definition_notes —
Todd's marker is the national marriage date, as his usage reads it.
Countries where marriage remains unlegalized have NO row (an absent
row is the honest state; a 0 would invent a date).

### `universal_suffrage_introduction.csv` — the anthropological fingerprint

16 countries, 1848-1946 (Todd's own named set — Sweden, Austria,
Belgium, the UK, Norway — extended to the European core his maps
compare against). The year the franchise arrived AS THE
HISTORIOGRAPHY DATES IT: for the 19th-century introductions that IS
the male grant (they were called "suffrage universel" at the time —
France 1848, Germany 1871, Austria 1907, Belgium 1919, Sweden 1911,
the UK 1918), for the later ones the completing women's grant (Norway
1913, Denmark 1915, the Netherlands 1919). The male/female
decomposition rides EVERY row's definition_note — Todd's own
convention (his corpus label prints "1911/1921" for Sweden), applied
uniformly, never hidden in a footnote.

**Gate check:**
- (a) todd_ref: L'invention de l'Europe (1990), 7 citations — the
  book's comparative-anthropology core (the exogamous-communal West
  universalizing early and from below, the authoritarian belt late
  and from above).
- (b) distortion = absence: no machine-readable door (probed live);
  the reference is Caramani's print electoral archive.
- (c) citations: per-row, the standard scholarly dating (Caramani
  2003, The Societies of Europe: Elections in Western Europe since
  1815, and the consensus of the electoral-history literature), with
  the national statutory milestones named (the 1906-12-21 Austrian
  amendment, the 1919-04-09 Belgian one-man-one-vote law, the
  1913-06-11 Norwegian constitutional amendment).

**Deliberately NOT done here:** no dating-convention harmonization
beyond what the historiography itself prints (the row's year follows
ITS country's standard dating; the note carries the decomposition);
countries outside the European comparison set have no row (the honest
absent state).

## The consensus-literature series (v17) — the tier's third family

A different shape again from both the founding series and the markers:
not one point per country (a dated event), not one continuous series
(one institution's print history), but a SPARSE PANEL of published
readings — the vintages each country's literature actually prints,
each with its own study, sample and union-type perimeter.

### `consanguineous_marriage_rate.csv` — the backlog's head claimed

102 rows, 69 countries, 1943-2021. The corpus's #6 (34 citations, 10
books — Le Destin des immigrés alone carries 16; Après l'Empire's DHS
table reads "Sudan 57% to Turkey 15%"; Qui est Charlie ?'s Maghreb
~25-35%). The value = the study's printed overall
consanguineous-marriage rate in percent over the union types THAT
study counts (the types ride every note: most count D1C,1C,11/2C,2C;
Bahrain 2009 counts first cousins only — the perimeter is the note's
job, the number is never converted).

**Gate check:**
- (a) todd_ref: the corpus's #6, the heaviest single-book concentration
  after the #1 (Le Destin des immigrés 16).
- (b) distortion = absence: no machine-readable door anywhere (the
  v16 probe record: GHO 0 hit, WDI 0/25000, OWID 404 on every
  candidate slug; the DHS surveys are microdata releases, not series
  doors) — probed live 2026-09-20, recorded in config/sources.yaml.
- (c) citations: per-row, the study itself — the consang.net global
  tables (A.H. Bittles' compilation, the domain's standard reference)
  carrying the national surveys and dispensation registries, PLUS the
  readings verified directly from the collected evidence: the PDHS
  2017-18 final report's Table 4.5 (Pakistan 63.9, married-to-a-
  relative, N=12,364, read from the saved report text), El-Mouzan et
  al. 2008 (Saudi national 56.0), Saadat et al. 2004 (Iran national
  38.6 over 306,343 couples), Ben Halim et al. 2012 (Tunisia's
  representative control cohort 29.8), Kalam et al. 2024 (India's
  NFHS-4+5 pooled national 13.6), Kaplan et al. 2016 (Turkey's
  Ministry-of-Health national 18.5). Every row was READ from a saved
  evidence file at generation time (scripts/v17_probe/consang/
  build_curated_table.py) — the v16 fixture-discipline lesson applied
  to the catalog itself.

**Conventions (documented per row, never applied silently):**
- year = the END year of the study's printed measurement period
  ('1956/57' -> 1957); the publication year where the compilation
  prints no period (El-Alfi et al. 1969 -> 1969); the decade's end
  for a fuzzy '1970s' (1979). The source's own period string rides
  every note.
- Scope discipline: national readings first; where no national print
  exists, the largest-sample subnational or community study (each
  flagged SUBNATIONAL in its note, the alternative prints documented
  on the same row). The two Israels are the Arab community's own
  national surveys — the scope is the study's, the note says so.
- Where several studies print the same (country, year), the
  largest-sample reading is entered and the others ride the note
  (Egypt 1983's multi-site arms; Syria 2008's urban/rural pair — the
  rural arm documented, no aggregate invented).

**Deliberately NOT done here:** no perimeter harmonization across
studies (a rate over first-cousins-only is NOT re-scaled to the
all-types basis — the perimeter rides the note, the comparability is
the reader's with the note's help); no interpolation between vintages
(the sparse panel is the metric's honest shape); Todd's own divergent
prints documented where they differ from the entered readings (his
Sudan 57% vs the compilation's Khartoum 52.0 — as-reported on both
ends); the 19th-century face (his historical France/Algeria tables)
waits for a citable print — the table starts 1943.

## Adding a new curated series

1. Check the gate (all three conditions — write them in the PR).
2. Add `catalog/curated/{name}.csv` with the exact column format above.
3. Reference it in the indicator's `sources` with
   `provider: curated, ref: {name}` (and `role`/`unit` per ADR-0008).
4. The connector, snapshot, normalize, merge and dist plumbing is
   already generic — no code change needed.
