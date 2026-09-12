"""Schema for an indicator — the identity card of each metric.

One YAML file in config/indicators/ = one instance of this model. The
pipeline refuses to start if a file doesn't validate against this schema:
better an explicit build failure than a silently incomplete or inconsistent
output JSON.
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator


class Family(str, Enum):
    mortality = "mortality"
    anthropometry_health = "anthropometry_health"
    society = "society"


class Reliability(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class Provider(str, Enum):
    owid = "owid"
    worldbank = "worldbank"
    who_gho = "who_gho"
    un_dyb = "un_dyb"
    curated = "curated"
    oecd = "oecd"


# Layer of the sourcing stack each provider occupies (ADR-0007 tiers;
# the human-readable narrative lives in config/sources.yaml, this map is
# the executable truth the dist carries per source):
#   curated  = L0-L2: hand-entered, one-citation-per-point official or
#              scholarly series (committed CSVs in catalog/curated/);
#   collector = L1-collector: national official statistics republished
#              as reported by an international collector (UN DYB); the
#              OECD DF_COM entry below is the SAME judgment for content
#              (WHO Mortality Database registrations as submitted — not
#              modeled; contrast with who_gho, whose homicide indicators
#              are literally named "Estimates of ...");
#   harmonized = L3 model estimates for cross-country comparability
#              (UN IGME via OWID, WDI, GHO) — for OWID this describes the
#              *content* of the pilot charts: the provider itself is an
#              honest L4 redistribution of the L3 estimates.
PROVIDER_LAYER: dict["Provider", str] = {
    Provider.curated: "curated",
    Provider.un_dyb: "collector",
    Provider.oecd: "collector",
    Provider.owid: "harmonized",
    Provider.worldbank: "harmonized",
    Provider.who_gho: "harmonized",
}

# How each provider's sources are cited in the dist (P2, the witness-
# citation gap of the external review): a human-readable citation string
# per source, formatted from the source_ref, plus the license its data
# carries. These mirror config/sources.yaml's narrative blocks (base_url /
# license_default) — keep the two in sync when a provider is added; the
# YAML is the human story, this map is the executable truth the dist emits.
PROVIDER_CITATION: dict["Provider", str] = {
    Provider.curated: "Hand-curated series '{ref}' (catalog/curated/, one citation per point)",
    Provider.un_dyb: "United Nations Statistics Division, Demographic Yearbook {edition}, Table {table}",
    Provider.owid: "Our World in Data, grapher dataset '{ref}'",
    Provider.worldbank: "World Bank Open Data API, indicator '{ref}'",
    Provider.who_gho: "WHO Global Health Observatory (GHO) API, indicator '{ref}'",
    Provider.oecd: "OECD, Causes of mortality (DF_COM), death cause '{cause}' - WHO Mortality Database redistribution",
}
PROVIDER_LICENSE: dict["Provider", str] = {
    Provider.curated: "Facts with citation (small extracts, clearly attributed) — see docs/licenses.md",
    Provider.un_dyb: "UN data reuse policy (attribution required, no endorsement implied)",
    Provider.owid: "CC-BY-4.0",
    Provider.worldbank: "CC-BY-4.0",
    Provider.who_gho: "CC-BY-3.0-IGO",
    Provider.oecd: "OECD Terms and Conditions, attribution required (content: WHO Mortality Database)",
}


class SourceRole(str, Enum):
    """ADR-0007/ADR-0008: how a source participates in an indicator.

    - `canonical`: feeds the indicator's canonical series. Duplicates
      across canonical sources are arbitrated by `priority` (an
      authenticity-tier-internal mechanism — never a cross-layer blend).
    - `witness`: stored, validated and displayed BESIDE the canonical
      series as divergence. Never merged into it, never averaged with
      it. The Todd board reads the canonical (as-reported) tier; the
      harmonized tier rides as witness (ADR-0008), and the Extra board
      reads the same dist with the witness as its display series.
    """

    canonical = "canonical"
    witness = "witness"


class SourceRef(BaseModel):
    provider: Provider
    # This indicator's identifier WITHIN that source (OWID slug, World Bank
    # code, GHO code, DYB "edition/table", curated CSV name...). The exact
    # meaning depends on the provider.
    ref: str
    # Column to use if the source exposes several values per row (e.g.
    # multi-variable OWID CSV, DYB number-vs-rate blocks). None = single
    # column auto-detected.
    field: str | None = None
    # Priority rank in case of an inter-source duplicate for the same
    # (entity, year): 1 = highest priority. Must be unique within a given
    # indicator (see validator below). Only canonical sources are ever
    # arbitrated by it (witnesses never enter arbitration — ADR-0007).
    priority: int = Field(..., ge=1)
    # Role in the canonical/witnesses model. Defaults to canonical, which
    # keeps every pre-ADR-0008 single-source indicator config valid.
    role: SourceRole = SourceRole.canonical
    # The NATIVE unit of this source's raw values, when it differs from the
    # indicator's canonical `unit`. Declared explicitly per source — the
    # conversion is applied by normalize.py through its declared lookup
    # table (never a guessed factor). None = source is already in the
    # canonical unit.
    unit: str | None = None


class PlausibleRange(BaseModel):
    """Bounds used by validate.py as a plausibility guard — NOT a scientific
    ground truth, just a safety net against unit/entry errors."""
    min: float | None = None
    max: float | None = None


class Indicator(BaseModel):
    id: str = Field(..., pattern=r"^[a-z][a-z0-9_]*$")
    label: str
    family: Family
    unit: str
    higher_is_better: bool

    todd_core: bool = Field(
        ..., description="True = used by Todd in his books (Todd mode). False = added in Extra mode only."
    )

    sources: list[SourceRef] = Field(..., min_length=1)

    coverage_start: int | None = None
    coverage_end: int | None = None

    reliability: Reliability
    reliability_criteria: str = Field(
        ..., description="One-sentence justification for the reliability level — never a bare label (see architecture review)."
    )
    reclassification_sensitive: bool = Field(
        default=False,
        description="True if the indicator is exposed to cause-of-death reclassification bias (suicides, cirrhosis...).",
    )

    plausible_range: PlausibleRange | None = None
    companion_indicators: list[str] = Field(default_factory=list)

    license: str
    notes: str | None = None

    @field_validator("label", "reliability_criteria", "notes", "unit", "license", mode="before")
    @classmethod
    def _strip_whitespace(cls, v: str | None) -> str | None:
        # YAML folded block scalars (">") leave a trailing \n — cleaned up
        # here rather than polluting every config file.
        return v.strip() if isinstance(v, str) else v

    @field_validator("sources")
    @classmethod
    def _unique_priorities(cls, sources: list[SourceRef]) -> list[SourceRef]:
        priorities = [s.priority for s in sources]
        if len(priorities) != len(set(priorities)):
            raise ValueError("source priorities must be unique within a given indicator")
        return sources

    @model_validator(mode="after")
    def _low_reliability_consistency(self) -> "Indicator":
        # Enforces the brief's cross-cutting principle: never a composite on
        # "low" reliability data without a visible warning. We can't stop
        # the frontend from using it, but we can force a written
        # justification here — it's this exact value that will be shown as
        # the warning.
        if self.reliability == Reliability.low and len(self.reliability_criteria) < 15:
            raise ValueError(
                f"{self.id}: reliability=low requires a detailed reliability_criteria (>=15 chars), "
                "not a vague justification — this value is what gets displayed as the warning."
            )
        return self

    @model_validator(mode="after")
    def _at_least_one_canonical_source(self) -> "Indicator":
        # ADR-0007/0008: an indicator without a canonical source would have
        # an empty main series with only witnesses around it — a config
        # error, not a legitimate "witnesses-only" display mode. If that
        # mode is ever wanted, it deserves its own explicit decision.
        if not any(s.role == SourceRole.canonical for s in self.sources):
            raise ValueError(
                f"{self.id}: no canonical source declared — every indicator needs at least "
                "one source with role=canonical (witnesses supplement it, never replace it)."
            )
        return self

    def sources_by_priority(self) -> list[SourceRef]:
        return sorted(self.sources, key=lambda s: s.priority)
