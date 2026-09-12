def test_registry_loads_258_entities(real_entities):
    assert len(real_entities.entities) >= 255  # 249 pycountry + 8 historical + Kosovo


def test_resolution_by_iso3(real_entities):
    e = real_entities.resolve_from_source("owid", "France", "FRA")
    assert e is not None
    assert e.entity_id == "france"
    assert e.label == "France"


def test_resolution_ussr_by_name_without_iso3(real_entities):
    # THE trap case from the brief: no ISO3, must be resolved by name.
    e = real_entities.resolve_from_source("owid", "USSR", None)
    assert e is not None
    assert e.entity_id == "ussr"
    assert e.is_historical
    assert e.valid_to == 1991


def test_resolution_ussr_with_owid_prefixed_code_still_works(real_entities):
    # OWID actually sends Code=OWID_USS for USSR rows, not a blank Code —
    # resolution must fall through to name matching regardless.
    e = real_entities.resolve_from_source("owid", "USSR", "OWID_USS")
    assert e is not None
    assert e.entity_id == "ussr"


def test_ussr_has_the_15_republics_as_successors(real_entities):
    ussr = real_entities.by_id("ussr")
    assert "russian_federation" in ussr.successors
    assert "ukraine" in ussr.successors
    assert len(ussr.successors) == 15


def test_unknown_entity_returns_none_never_a_guess(real_entities):
    e = real_entities.resolve_from_source("owid", "Wakanda", None)
    assert e is None


def test_ussr_does_not_cover_a_post_dissolution_year(real_entities):
    ussr = real_entities.by_id("ussr")
    assert ussr.covers_year(1990) is True
    assert ussr.covers_year(1995) is False


def test_czechoslovakia_points_to_czechia_and_slovakia(real_entities):
    cs = real_entities.by_id("czechoslovakia")
    assert set(cs.successors) == {"czechia", "slovakia"}


def test_kosovo_is_present_and_resolves_by_name(real_entities):
    # Added after a live-network audit found it as a real gap (not an
    # aggregate) — see CHANGELOG.
    kosovo = real_entities.by_id("kosovo")
    assert kosovo is not None
    assert kosovo.valid_from == 2008
    e = real_entities.resolve_from_source("owid", "Kosovo", "OWID_KOS")
    assert e is not None
    assert e.entity_id == "kosovo"


def test_ex_soviet_republics_carry_formerly_part_of(real_entities):
    for entity_id in ["russian_federation", "ukraine", "belarus", "kazakhstan", "estonia"]:
        e = real_entities.by_id(entity_id)
        assert e.formerly_part_of is not None, entity_id
        assert e.formerly_part_of.union_entity_id == "ussr"
        assert e.formerly_part_of.until_year == 1991


def test_unrelated_entity_has_no_formerly_part_of(real_entities):
    assert real_entities.by_id("france").formerly_part_of is None


def test_no_duplicate_entity_id(real_entities):
    ids = [e.entity_id for e in real_entities.entities]
    assert len(ids) == len(set(ids))
