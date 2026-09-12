"""fetch: network -> data/raw/{provider}/{indicator_id}/{timestamp}.json

The only pipeline step that touches the network. Deliberately separated
from normalize/merge/validate/build so that `rebuild` can run without
network access from the last known raw data (useful in a sandbox, in dev,
or to replay a normalization bugfix without re-downloading).

Each source is fetched independently: one source failing (network error,
HTTP error, unexpected CSV shape) must NOT prevent the other sources or
other indicators from being fetched. This was a real bug in an earlier
version — see CHANGELOG entry "fetch isolation" — caught by a live-network
audit where a single 403 on one indicator silently killed the whole run.
"""
from __future__ import annotations

import dataclasses
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from src.connectors.base import Connector, RawFetchResult
from src.connectors.curated import CuratedConnector
from src.connectors.dyb import DybConnector
from src.connectors.oecd import OecdConnector
from src.connectors.owid import OwidConnector
from src.schema.indicator import Indicator, Provider

logger = logging.getLogger(__name__)

CONNECTORS: dict[Provider, Connector] = {
    Provider.owid: OwidConnector(),
    Provider.un_dyb: DybConnector(),
    Provider.oecd: OecdConnector(),  # DF_COM: WHO Mortality Database via SDMX (P3)
    Provider.curated: CuratedConnector(),  # no network: "fetch" = read catalog/curated/{ref}.csv
    # Provider.worldbank and Provider.who_gho: phase 5, deliberately absent.
}
# ADR-0007/0008 wiring state: un_dyb (collector tier) and curated (L0-L2)
# are the CANONICAL sources of infant_mortality (authenticity first), with
# owid as the harmonized witness — the unit conversion they required is
# now implemented in normalize.py's declared lookup table.


@dataclass
class FetchFailure:
    indicator_id: str
    provider: str
    source_ref: str
    error: str


@dataclass
class FetchOutcome:
    written: list[Path] = field(default_factory=list)
    failures: list[FetchFailure] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return len(self.failures) == 0


def fetch_indicator(indicator: Indicator, raw_dir: Path) -> FetchOutcome:
    """Fetch every source of an indicator for which a connector is available.

    A source whose provider has no connector yet (worldbank, who_gho in
    phase 1) is explicitly logged as SKIPPED, never silently ignored. A
    source that raises during fetch is caught, logged, and recorded as a
    failure — it does NOT stop the other sources of this indicator, nor the
    rest of the run (see fetch_all).
    """
    outcome = FetchOutcome()
    for source in indicator.sources_by_priority():
        connector = CONNECTORS.get(source.provider)
        if connector is None:
            logger.warning(
                "SKIP %s / %s: no connector registered for provider '%s' (later phase)",
                indicator.id, source.ref, source.provider.value,
            )
            continue

        logger.info("FETCH %s <- %s:%s", indicator.id, source.provider.value, source.ref)
        try:
            result = connector.fetch_raw(source.ref, indicator.id, field=source.field)
        except Exception as e:  # noqa: BLE001 - deliberately broad: any failure here must not kill the run
            logger.error("FAILED %s / %s: %s", indicator.id, source.ref, e)
            outcome.failures.append(
                FetchFailure(indicator_id=indicator.id, provider=source.provider.value, source_ref=source.ref, error=str(e))
            )
            continue

        path = _write_snapshot(result, raw_dir)
        logger.info("  -> %d rows, snapshot %s", len(result.records), path)
        outcome.written.append(path)
    return outcome


def _write_snapshot(result: RawFetchResult, raw_dir: Path) -> Path:
    # Per-source_ref layout (see normalize._source_dir): one directory per
    # (provider, indicator, source_ref) so several sources of the SAME
    # provider can coexist (DYB editions loop) without shadowing each other.
    out_dir = raw_dir / result.provider / result.indicator_id / result.source_ref.replace("/", "_")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{result.fetched_at}.json"
    payload = {
        "provider": result.provider,
        "source_ref": result.source_ref,
        "indicator_id": result.indicator_id,
        "fetched_at": result.fetched_at,
        "source_url": result.source_url,
        "records": [dataclasses.asdict(r) for r in result.records],
    }
    if result.footnotes:
        # The source's own footnote legend/texts (P2) — the DYB Footnotes
        # worksheet. Omitted (not null-filled) for providers that print none.
        payload["footnotes"] = result.footnotes
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def fetch_all(indicators: dict[str, Indicator], raw_dir: Path) -> FetchOutcome:
    combined = FetchOutcome()
    for indicator in indicators.values():
        outcome = fetch_indicator(indicator, raw_dir)
        combined.written.extend(outcome.written)
        combined.failures.extend(outcome.failures)
    return combined
