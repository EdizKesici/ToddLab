"""Common interface for all source connectors.

Deliberate separation between:
- a PURE parsing function (testable offline, no network)
- a network fetch method (thin, not exercised in the CI sandbox, but trivial)

This is what makes it possible to validate all business logic (normalize,
merge, validate, build) with fixtures, independently of network availability.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class RawRecord:
    """A raw row exactly as reported by the source, BEFORE entity resolution
    and unit conversion. entity_raw_name / iso3_raw come straight from the
    source — normalize.py is what resolves them into an Entity.

    citation / definition_note are optional per-point provenance, carried
    by sources that print it next to the number (the curated tier carries
    them on EVERY row by construction — the curation gate's condition (c);
    ADR-0007). They are not interpreted by the pipeline, only transported
    to the dist so the frontend can display them.

    sex carries the demographic breakdown when the source prints one (UN
    DYB Table 4 prints life expectancy at birth for Male and Female
    separately — there is no "both sexes" column to report). It stays None
    for every other source; (entity, year, sex) is the merge key, so a
    sex-split canonical series and a both-sexes witness series coexist
    without colliding. Averaging male+female into a both-sexes value would
    be a derivation — the canonical tier reports, it does not derive.

    The quality_* / footnote_* fields (P2) carry the collector's OWN
    annotations, transported as-reported and never interpreted:
    - quality_code: the DYB's row code ("C" >=90% complete civil
      registration, "U" <90%, "|" other reliable source, "+" prefix =
      tabulated by registration date rather than occurrence date);
    - footnote_refs: the footnote numbers printed next to the value
      (country-, row- and cell-level, reading order), whose TEXTS live in
      the snapshot's `footnotes` block and are joined into the dist;
    - reference_range: the printed reference period of the value, in the
      source's own syntax — Table 4's Roman numeral next to the LE value
      (III = 3-year period; the width), or Table 21/22's explicit period
      string ("2012 - 2015") whose END year is the point's year (the
      DYB's own convention, verified edition by edition against Table 4);
      a Todd-relevant as-reported nuance;
    - missing_marker: WHICH marker was printed where the value is absent
      ("..." = not available, "-" = nil/not applicable) — an explicit gap
      with its printed reason, never silently conflated;
    - provisional: the "*" marker (the DYB's own "provisional" flag);
    - small_base: the "\u2666" marker (Table 17: "Ratios based on 30 or
      fewer maternal deaths are identified by the symbol ♦" — the printed
      Notes17 text; a small-numbers caveat on the RATIO, as-reported).

    v22 (the bilateral face): origin_raw_name / origin_iso3_raw carry the
    SECOND axis of a matrix row when the source prints one — Eurostat's
    migr_pop3ctb c_birth (the by-birth origin of a destination's stock,
    the ROW door) and the OECD DF_MIG_POPF BIRTH_COUNTRY. On such records
    entity_raw_name/iso3_raw are the DESTINATION and origin_* the ORIGIN
    — Todd's Le Destin des immigrés board shape ("the stock of Moroccans
    IN France"). None on every pre-v22 record: the single-axis face; the
    pipeline routes on the field's presence (origin set -> the bilateral
    layer, never the (entity, year) merge key).
    """
    entity_raw_name: str
    iso3_raw: str | None
    year: int
    value: float | None  # None = explicitly missing value (not 0, not interpolated)
    # v22: the origin axis of a bilateral matrix row (None = single-axis).
    origin_raw_name: str | None = None
    origin_iso3_raw: str | None = None
    citation: str | None = None
    definition_note: str | None = None
    sex: str | None = None
    quality_code: str | None = None
    footnote_refs: list[str] | None = None
    reference_range: str | None = None
    missing_marker: str | None = None
    provisional: bool | None = None
    small_base: bool | None = None


@dataclass
class RawFetchResult:
    provider: str
    source_ref: str  # OWID slug / World Bank code / GHO code
    indicator_id: str
    fetched_at: str  # ISO 8601 UTC, format: %Y-%m-%dT%H%M%SZ (see now_iso below)
    source_url: str
    records: list[RawRecord] = field(default_factory=list)
    # The source's own footnote LEGEND and TEXTS (DYB: the "Footnotes"
    # worksheet — the code legend, the Roman-numeral legend, the numbered
    # per-country/per-value notes). Transported verbatim, joined into the
    # dist for the refs the emitted points actually carry (P2). None for
    # providers that print no footnotes.
    footnotes: dict | None = None

    @staticmethod
    def now_iso() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")


class Connector(ABC):
    provider: str

    @abstractmethod
    def fetch_raw(self, source_ref: str, indicator_id: str, field: str | None = None) -> RawFetchResult:
        """Fetch from the network and return a RawFetchResult.
        Must raise an explicit exception (never return an empty result
        silently) on network failure or unexpected response."""
        raise NotImplementedError
