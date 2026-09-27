# ADR-0010: The two bilateral faces are parallel layers, never merged

- **Status**: Accepted (2026-09-25)
- **Scope**: how the dist carries the two legal decompositions of the
  immigrant stock (place of birth vs citizenship); what the merge may
  never do across them; the vocabulary that names them
- **Depends on**: ADR-0007 (source-of-record and witnesses — the
  never-a-cross-layer-blend rule this ADR extends to a second axis),
  v22's `bilateral` layer (the birth face, CHANGELOG 2026-09-22)

## Context

v22 wired the bilateral (destination x origin) decomposition of
`immigration_stock` on the place-of-birth axis: Eurostat `migr_pop3ctb`
ROW doors (canonical) + the OECD questionnaire's foreign-born matrix
`DSD_MIG_F@DF_MIG_POPF` (witness). But Todd's own boards read the SAME
migrants through TWO legalities — *immigrés* (born abroad) vs
*étrangers* (holding a foreign nationality), the pair Le Destin des
immigrés itself carries — and the two faces DIVERGE exactly where
naturalization runs ahead of the census (FR<-MA 2015: 954,742 born vs
458,561 citizens, verified live on both doors 2026-09-25) and CONVERGE
where it rarely does (FR<-PT 2015: 648,112 vs 541,867). The same
questionnaires print both faces: Eurostat `migr_pop1ctz` mirrors
`migr_pop3ctb` with `citizen` in `c_birth`'s stride, and the OECD
serves the sibling flow `DSD_MIG@DF_MIG` measure B15 beside B14 (the
two flows are ACCESS MIRRORS: each refuses the wire the other serves —
verified live).

The question this ADR answers: when one indicator has TWO bilateral
faces over the SAME (destination, origin, year) key space, does the
merge arbitrate between them, blend them, or carry them separately?

## Decision

1. **The dist carries TWO parallel layers, never merged.** `bilateral`
   (the birth face, v22) and `bilateral_citizenship` (the legal face,
   v23) are separate keys in the indicator's dist payload, each with
   its own `data` and its own `witnesses`. A (destination, origin,
   year) key that prints on both faces exists TWICE, once per layer,
   with each face's own value — the divergence IS the display
   (the CONVERGE/DIVERGE contrasts the layer exists to show).
2. **The merge never arbitrates across faces.** The arbitration key
   (destination, origin, year, sex) is shared VERBATIM, but the key
   SPACES are separate files: `{id}.bilateral.json` vs
   `{id}.bilateral_citizenship.json`, merged by the same machinery into
   separate `.merged.json` / `.witnesses.json` pairs. A birth-face
   value and a citizenship-face value can never collide, shadow, or
   average each other — the ADR-0007 never-a-cross-layer-blend rule,
   extended from the canonical/witness axis to the legality axis.
3. **The routing key is `RawRecord.origin_axis`** — `"birth"` |
   `"citizenship"` | `None` (single-axis, or a pre-v23 snapshot: the
   birth face is the default by construction, so v22 raw trees rebuild
   bit-identically on v23 code). The connectors stamp it; normalize
   routes on it; the dist layer names follow it. The field is additive:
   no pre-existing record is modified.
4. **Same drop discipline, same entity admission, per face.** Both
   faces drop the diagonal (the native face — born or national,
   respectively), the summary codes and the aggregates logged per
   class; the citizenship face adds STLS (stateless — a nationality
   without a state, an axis residual the birth face never printed).
   The vanished-entity codes (Eurostat AN, the OECD _F prints, XKV)
   ride the SAME override tables onto their withdrawn ISO3 entities on
   both faces: people born in Czechoslovakia and people still holding
   its nationality are both the as-printed classification.
5. **The faces' own geographies are carried as-printed, never
   "corrected".** Germany joins the citizenship face (its birth-face
   row never printed the detail), Cyprus leaves it — the
   registrations' own shape, the same honest-absence class as the
   birth face's 14 totals-only geos.

## Consequences

**Positive**: the Todd question the pair exists for (how much of the
foreign-born stock has naturalized, per origin) becomes a one-file
comparison instead of an unanswerable blend; the v22 contract survives
byte-identically (the new layer is additive — the same guarantee the
`bilateral` layer itself shipped with); a future third face (by-sex,
the recorded V24 hook) extends the pattern one routing value at a time.

**Negative (accepted)**: the dist file grows (the citizenship layer
adds 112,058 canonical + 109,763 witness points); consumers must read
two keys to compare faces (a derived "gap" product would be a
derivation — deliberately out of scope, the same line that keeps a
both-sexes canonical life expectancy out); the two faces' coverage
differs (34 vs 30 Eurostat destinations) and the asymmetry must be
explained wherever the pair is displayed.

**Neutral**: the merge/validate/build machinery is shared and
parameterized by layer name (one helper, two calls — the v22 inline
block extracted); the provenance trail carries `layer:
"bilateral_citizenship"` entries self-describing, one trail for both
faces.
