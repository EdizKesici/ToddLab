"""Schema for a geographic entity (current country or defunct historical entity).

This is the most sensitive piece of the project: it carries all the logic
for resolving border changes (USSR, Czechoslovakia, Yugoslavia...) flagged
as trap #1 in the original brief. It is deliberately kept separate from the
indicator schema so it can be audited/corrected independently.
"""
from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class FormerUnionMembership(BaseModel):
    """Flags that, before `until_year`, this entity's data may actually
    represent a larger political union it was part of (e.g. the USSR), not
    this entity governed independently.

    Deliberately distinct from predecessor/successor: Czechia genuinely did
    not exist as a state before 1993 (predecessor = czechoslovakia is a
    real discontinuity), whereas Russia, Ukraine, Kazakhstan etc. existed
    continuously as geographic/administrative units before, during, and
    after the USSR — only their sovereign status changed, and OWID's data
    (Gapminder/UN IGME-sourced) attaches the historical values straight to
    their modern country code rather than to a separate "USSR" entity. A
    live-network audit confirmed OWID carries no standalone "USSR" entity
    at all in either of the two mortality datasets checked, even the
    1751-2024 long-run one — see CHANGELOG. Decision: show each ex-Soviet
    republic's series continuously (pre- and post-1991 in one line) rather
    than fabricate a separate "ussr" data series, with this field driving
    a frontend warning for the pre-1991 portion.
    """
    union_entity_id: str
    until_year: int
    note: str


class SourceIds(BaseModel):
    """This entity's identifier as used by each external source.

    `None` explicitly means "this source has no code for this entity" (e.g.
    a source that didn't exist before the entity was dissolved) — to be
    distinguished from a missing field, which would be a config error.
    """

    owid: str | None = None
    worldbank: str | None = None
    who_gho: str | None = None
    # Entity name AS PRINTED in UN Demographic Yearbook tables, when it
    # differs from `label` (e.g. label "Bolivia" vs DYB "Bolivia
    # (Plurinational State of)"). Each entry was verified against the live
    # DYB Table 15 file — this is the same incremental-correction mechanism
    # as the OWID names, never a guessed alias.
    un_dyb: str | None = None


class Entity(BaseModel):
    entity_id: str = Field(..., description="Canonical internal identifier, stable over time.")
    label: str
    iso3: str | None = Field(
        default=None,
        description="ISO 3166-1 alpha-3 code. None for entities that predate ISO or are disputed (e.g. USSR, Kosovo).",
    )

    valid_from: int | None = Field(default=None, description="First year this entity existed in this form.")
    valid_to: int | None = Field(default=None, description="Last year this entity existed in this form (None = still active).")

    predecessor: str | None = Field(default=None, description="entity_id this entity directly descends from, if any.")
    successors: list[str] = Field(default_factory=list, description="entity_id(s) that succeeded it after dissolution/split.")

    source_ids: SourceIds = Field(default_factory=SourceIds)
    formerly_part_of: FormerUnionMembership | None = None
    label_source: str = Field(
        default="manual",
        description="Provenance of label: 'pycountry' (generated from pycountry English names) or 'manual'.",
    )
    notes: str | None = None

    @model_validator(mode="after")
    def _temporal_consistency(self) -> "Entity":
        if self.valid_from is not None and self.valid_to is not None and self.valid_from > self.valid_to:
            raise ValueError(f"{self.entity_id}: valid_from ({self.valid_from}) is after valid_to ({self.valid_to})")
        return self

    @property
    def is_historical(self) -> bool:
        return self.valid_to is not None

    def covers_year(self, year: int) -> bool:
        if self.valid_from is not None and year < self.valid_from:
            return False
        if self.valid_to is not None and year > self.valid_to:
            return False
        return True


class EntityRegistry:
    """In-memory view of all entities, with the indexes the pipeline needs."""

    def __init__(self, entities: list[Entity]):
        self.entities = entities
        self._by_id = {e.entity_id: e for e in entities}
        self._by_owid_name = {e.source_ids.owid: e for e in entities if e.source_ids.owid}
        self._by_dyb_name = {e.source_ids.un_dyb: e for e in entities if e.source_ids.un_dyb}
        self._by_label = {e.label: e for e in entities}
        self._by_iso3 = {e.iso3: e for e in entities if e.iso3}

        dupes = [eid for eid in self._by_id if list(self._by_id).count(eid) > 1]
        if len(self._by_id) != len(entities):
            raise ValueError(f"Duplicate entity_id in entities.yaml: {dupes}")
        if len(self._by_label) != len(entities):
            raise ValueError(
                "Duplicate entity label in entities.yaml: "
                f"{sorted(e.label for e in entities if [x.label for x in entities].count(e.label) > 1)}"
            )

    def by_id(self, entity_id: str) -> Entity | None:
        return self._by_id.get(entity_id)

    def by_owid_name(self, name: str) -> Entity | None:
        return self._by_owid_name.get(name)

    def by_dyb_name(self, name: str) -> Entity | None:
        return self._by_dyb_name.get(name)

    def by_label(self, label: str) -> Entity | None:
        return self._by_label.get(label)

    def by_iso3(self, code: str) -> Entity | None:
        return self._by_iso3.get(code) if code else None

    def resolve_from_source(self, provider: str, raw_name: str, iso3_code: str | None) -> Entity | None:
        """Resolve a (raw name, optional ISO3 code) pair from a source into a canonical Entity.

        Strategy: ISO3 first (reliable, unambiguous), then exact per-source
        name (needed for defunct entities with no ISO3, e.g. USSR). NEVER
        guesses by string similarity: an unresolved name must surface as an
        explicit gap, not get attached at random to the closest-looking entity.

        Note: OWID uses "OWID_"-prefixed pseudo-codes (e.g. OWID_USS,
        OWID_KOS, OWID_WRL) for aggregates, regions, and historical/disputed
        entities that have no formal ISO3 — NOT an empty Code field as an
        earlier version of this docstring incorrectly assumed. Those
        pseudo-codes simply won't match anything in `_by_iso3` (which is
        keyed by real ISO3 only), so resolution correctly falls through to
        the name-based lookup below.

        Per-provider exact-name fallbacks (ADR-0007/0008):
        - `curated` tables are written with canonical entity_ids on purpose
          (they are OUR files, reviewed in git), so `raw_name` IS the
          entity_id: resolved by exact id. A typo lands in unresolved.json
          like any other source — curated does not get silent forgiveness.
        - `un_dyb` tables print the UN's own country names: resolved by the
          entity's declared `source_ids.un_dyb` override first, then by
          exact label (the DYB's English name usually equals the pycountry
          label; the mismatches get an explicit `un_dyb` override in
          entities.yaml, verified against the live table).
        """
        if iso3_code:
            entity = self.by_iso3(iso3_code)
            if entity:
                return entity
        if provider == "owid":
            return self.by_owid_name(raw_name)
        if provider == "curated":
            return self.by_id(raw_name)
        if provider == "un_dyb":
            return self.by_dyb_name(raw_name) or self.by_label(raw_name)
        return None

    @classmethod
    def from_yaml(cls, data: list[dict]) -> "EntityRegistry":
        return cls([Entity.model_validate(item) for item in data])
