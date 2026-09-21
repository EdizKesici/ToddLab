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
    # v15: the corpus's own vocabulary carries a 'markers' family (Todd's
    # dated institutional events — same-sex marriage legalization,
    # universal suffrage introduction: one year per country, a step the
    # board reads as a threshold, not a curve). The enum narrows when a
    # metric becomes an indicator, per todd_refs.py's schema note — these
    # two metrics are that family's first indicators.
    markers = "markers"
    # v17: the corpus's 'economy' family (63 citations across its 5
    # metrics — unemployment_rate 20, the industrial/employment shares,
    # the GDP-adjacent reads). unemployment_rate is that family's first
    # indicator; the same one-metric-at-a-time narrowing as markers.
    economy = "economy"


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
    eurostat = "eurostat"


# Root genealogy (v11, P5 — the-measurement-problem.md section 5.1): the
# ULTIMATE ORIGIN a source redistributes or republishes, as a closed
# vocabulary. Providers are doors; roots are where the numbers were made.
# The founding case: on infant mortality, OWID, the World Bank and GHO are
# three doors carrying ONE root (UN IGME) — "cross-confirming them against
# each other is an illusion of independent verification". The `root` field
# makes that claim executable: the catalog computes how many independent
# roots an indicator has and which providers are merely re-publishing the
# same one. Adding a root = a deliberate, reviewable registry edit (never
# an ad-hoc string in a config).
ROOT_LABELS: dict[str, str] = {
    "un_igme": "UN Inter-agency Group for Child Mortality Estimation (IGME)",
    "un_wpp": "UN Population Division, World Population Prospects (WPP)",
    "un_mmeig": "UN Maternal Mortality Estimation Inter-agency Group (MMEIG)",
    "who_mdb": "WHO Mortality Database (civil registration, as submitted by member states)",
    "unsd_dyb": "UN Statistics Division, Demographic Yearbook (questionnaire collector)",
    "unodc": "UN Office on Drugs and Crime (UNODC)",
    # v13 (suicide_rate witness): the WHO Global Health Estimates — the
    # modeled cause-of-death series, DISTINCT from who_mdb (the as-submitted
    # registrations the OECD door redistributes). The distinction is the
    # indicator's whole story: GHE re-distributes ill-defined causes over
    # the suicides the collectors printed (Russia 2000 male: 69.8 as-
    # reported via the OECD door vs 95.2 modeled, both verified live
    # 2026-09-19) — the root field is what keeps that divergence from
    # reading like a contradiction.
    "who_ghe": "WHO Global Health Estimates (GHE) — modeled cause-of-death estimates",
    "owid_longrun_composite": (
        "OWID long-run compilation (Riley/HMD historical reconstructions + UN WPP modern estimates)"
    ),
    "soviet_official": (
        "Official Soviet statistical series (TsSU yearbooks; Davis & Feshbach 1980 compilation)"
    ),
    # v14 (birth_rate_fertility canonical): Eurostat's demographic
    # collection — national official fertility series (the TFR each
    # statistical office computes and publishes), collected by Eurostat
    # via its own questionnaire, the same collector judgment as unsd_dyb
    # for content. THE REASON THIS ROOT EXISTS: the Todd corpus's #1
    # metric is TFR (111 citations, 16/16 books) and NO other living
    # collector wire prints it — the UN DYB publishes CBR (Table 9) and
    # age-specific rates (Table 10) but no TFR column (verified on the
    # 2024 file, 2026-09-19), and the OECD SDMX registry carries no
    # national fertility dataflow (DF_FERTILITY is TL2/TL3 regional,
    # verified live). Without this door the corpus's #1 would have had a
    # harmonized (WPP) canonical — a constitution break; with it, the
    # collector tier stands and the WPP doors ride as witnesses.
    "eurostat_demo": (
        "Eurostat demographic statistics (demo_find — national official fertility series collected by Eurostat)"
    ),
    # v15 (the markers): the dated national legislation the curated
    # marker tables carry — statutes, constitutional rulings, referendums,
    # each row's own citation being the primary source. A ROOT distinct
    # from every collector (the law is not collected, it is enacted): the
    # genealogy field's way of saying the marker tier has no upstream
    # redistributor to disclose — the citation IS the origin, which is
    # also why no witness can ever cross-check it (there is nothing
    # upstream to witness).
    "national_legislation": (
        "National legislation and constitutional rulings (the enacted law itself, cited per point)"
    ),
    # v16 (illegitimate_births witness): the OECD Family Database — the
    # OECD-compiled share of births outside marriage (SF2.4), reached
    # through OWID's chart door (the Family Database itself carries no
    # SDMX wire — the v14 registry finding). An OECD-COMPILED product:
    # the OECD assembles and standardizes national series, which makes
    # it a harmonized-family witness (the same relation WPP/GHE hold to
    # their collectors), NOT the as-submitted collector tier. The root
    # label is what lets the vintage divergence (OECD 2021 vintage vs
    # Eurostat's fresher prints) read as two doors, never a
    # contradiction.
    "oecd_family": (
        "OECD Family Database (SF family indicators, OECD-compiled; via OWID's chart door)"
    ),
    # v17 (consanguineous_marriage_rate canonical): the consanguinity-
    # studies literature — the national surveys, dispensation registries
    # and DHS reports the curated table carries, each row's own citation
    # being the primary source, vectored by Bittles' consang.net
    # compilation. Like national_legislation, a root with NO upstream
    # redistributor to disclose: no collector or harmonized door prints
    # the metric anywhere (probed live 2026-09-20: GHO 0 hit, WDI
    # 0/25000, OWID 404 — the gate finding), so the study IS the origin
    # and no witness can ever cross-check it (the same constitution as
    # the markers; the probe record lives in config/sources.yaml).
    "consanguinity_studies": (
        "The consanguinity-studies literature (national surveys and dispensation registries; "
        "Bittles' consang.net compilation + DHS final reports, cited per point)"
    ),
    # v17 (unemployment_rate canonical): Eurostat's labour-force
    # collection — the national official unemployment rates (each
    # statistical office's own LFS print, collected by Eurostat via its
    # questionnaire, 1-decimal as published), dataset une_rt_a pinned
    # age=Y15-74/unit=PC_ACT/sex=T. Distinct from eurostat_demo (the
    # demography collection): same collector judgment, different
    # questionnaire. The witness face is the ILO-processed LFS family
    # (ilo_lfs below) — on the co-covered core the two doors print the
    # same rates to rounding (FR 2015: Eurostat 10.4 vs WB/ILO 10.354,
    # verified live 2026-09-20), the same relation who_mdb/who_ghe hold.
    "eurostat_lfs": (
        "Eurostat labour-force statistics (une_rt_a — national official unemployment rates collected by Eurostat)"
    ),
    # v17 (unemployment_rate witness): the ILOSTAT LFS database —
    # national labour-force surveys RE-PROCESSED by the ILO (microdata
    # harmonization, "Repository: ILO-STATISTICS - Micro data processing",
    # LFS-ADJ adjusted series for Germany — the v17 probe record),
    # redistributed by World Bank WDI as SL.UEM.TOTL.NE.ZS "national
    # estimate" (byte-identical to the ILOSTAT DEAP plain rate on the
    # co-covered core, verified live). A harmonized-family witness for
    # the Eurostat collector: same underlying national surveys, one
    # harmonization step apart — the root pair that keeps the FR 2024
    # 7.436-vs-7.4 rounding seam and the DE 2005 11.193-vs-ABSENT
    # coverage seam reading as two doors, never a contradiction.
    "ilo_lfs": (
        "ILOSTAT LFS database (ILO-processed national labour-force surveys; redistributed by World Bank WDI as national estimate)"
    ),
}


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
    Provider.eurostat: "collector",
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
# v17: the Eurostat template carries the dataset's own API title (the
# registry below) — one questionnaire, one title, never a borrowed one.
EUROSTAT_DATASET_TITLES: dict[str, str] = {
    "demo_find": "Fertility indicators",
    "une_rt_a": "Unemployment by sex and age - annual data",
}
PROVIDER_CITATION: dict["Provider", str] = {
    Provider.curated: "Hand-curated series '{ref}' (catalog/curated/, one citation per point)",
    Provider.un_dyb: "United Nations Statistics Division, Demographic Yearbook {edition}, Table {table}",
    Provider.owid: "Our World in Data, grapher dataset '{ref}'",
    Provider.worldbank: "World Bank Open Data API, indicator '{ref}'",
    Provider.who_gho: "WHO Global Health Observatory (GHO) API, indicator '{ref}'",
    Provider.oecd: "OECD, Causes of mortality (DF_COM), death cause '{cause}' - WHO Mortality Database redistribution",
    Provider.eurostat: "Eurostat, {title} (dataset {dataset}), series '{code}'",
}
PROVIDER_LICENSE: dict["Provider", str] = {
    Provider.curated: "Facts with citation (small extracts, clearly attributed) — see docs/licenses.md",
    Provider.un_dyb: "UN data reuse policy (attribution required, no endorsement implied)",
    Provider.owid: "CC-BY-4.0",
    Provider.worldbank: "CC-BY-4.0",
    Provider.who_gho: "CC-BY-3.0-IGO",
    Provider.oecd: "OECD Terms and Conditions, attribution required (content: WHO Mortality Database)",
    Provider.eurostat: "Eurostat reuse policy (attribution required, no endorsement implied)",
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
    # Root genealogy (v11): the ultimate origin this source redistributes —
    # see ROOT_LABELS above. REQUIRED on every source so the genealogy can
    # never silently go missing when a new one is added; must belong to the
    # closed registry.
    root: str

    @field_validator("root")
    @classmethod
    def _known_root(cls, v: str) -> str:
        if v not in ROOT_LABELS:
            raise ValueError(
                f"unknown root {v!r} — declare it in ROOT_LABELS (src/schema/indicator.py) "
                f"first; known roots: {sorted(ROOT_LABELS)}"
            )
        return v


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
