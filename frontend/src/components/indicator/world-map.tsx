"use client";

import { geoNaturalEarth1, geoPath } from "d3-geo";
import type { FeatureCollection, GeoJsonProperties, Geometry } from "geojson";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import type { GeometryCollection, Topology } from "topojson-specification";
import { feature } from "topojson-client";
import { YearSlider } from "@/components/shared/year-slider";
import { SexToggle, type SexChoice } from "@/components/shared/sex-toggle";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardAction,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useEntities, useYearData } from "@/lib/toddlab/client";
import { fmtNumber, percentileOf } from "@/lib/toddlab/format";
import { useEntityLabel, useI18n, useUnitLabel } from "@/lib/toddlab/i18n";
import { cn } from "@/lib/utils";

/**
 * 5 fixed color bins, best → worst (teal → terracotta harmony).
 * Fixed hex colors: they sit on the same mid-luminance band in light and dark.
 */
const BIN_COLORS_BEST_TO_WORST = [
  "#0f766e",
  "#5e8a68",
  "#a08d5f",
  "#c07a4a",
  "#b8431f",
] as const;

const MAP_W = 780;
const MAP_H = 420;

interface WcCountry {
  cca3: string;
  ccn3: string;
}

interface TopoShape {
  key: string;
  d: string;
  numericId: string;
  topoName: string;
}

function binColor(percentile: number): string {
  const idx =
    percentile >= 80 ? 0 : percentile >= 60 ? 1 : percentile >= 40 ? 2 : percentile >= 20 ? 3 : 4;
  return BIN_COLORS_BEST_TO_WORST[idx];
}

export interface WorldMapProps {
  indicatorId: string;
  availableYears: number[];
  sexSplit: boolean;
  higherIsBetter: boolean;
  unit: string;
  /** Year & sex are lifted to the parent page so the map and the ranking share one source. */
  year: number | null;
  sex: SexChoice;
  onYearChange: (y: number) => void;
  onSexChange: (s: SexChoice) => void;
  /** Arrival from a country profile: outline that country on the map. */
  focusEntityId?: string | null;
}

export function WorldMap({
  indicatorId,
  availableYears,
  sexSplit,
  higherIsBetter,
  unit,
  year,
  sex,
  onYearChange,
  onSexChange,
  focusEntityId,
}: WorldMapProps) {
  const { t, lang } = useI18n();
  const router = useRouter();
  const entityLabel = useEntityLabel();
  const unitLabel = useUnitLabel();

  /* ------------------------------ Topology load ----------------------------- */
  // Dynamic imports keep topojson + world-countries out of the SSR bundle.
  const [topo, setTopo] = useState<Topology | null>(null);
  const [numericToIso3, setNumericToIso3] = useState<Map<string, string> | null>(null);

  useEffect(() => {
    let alive = true;
    (async () => {
      const topoMod = (await import("world-atlas/countries-110m.json")) as unknown as {
        default: Topology;
      };
      const wcMod = (await import("world-countries")) as unknown as {
        default: WcCountry[];
      };
      if (!alive) return;
      setTopo(topoMod.default);
      setNumericToIso3(
        new Map(
          wcMod.default
            .filter((c) => c.ccn3 && c.cca3)
            .map((c) => [c.ccn3, c.cca3] as const),
        ),
      );
    })().catch(() => undefined);
    return () => {
      alive = false;
    };
  }, []);

  /* ------------------------------ ISO3 → entity ----------------------------- */
  const { data: entitiesData } = useEntities();
  const iso3ToEntity = useMemo(() => {
    const m = new Map<string, string>();
    for (const e of entitiesData?.entities ?? []) {
      if (e.iso3 && !m.has(e.iso3)) m.set(e.iso3, e.entity_id);
    }
    return m;
  }, [entitiesData]);
  const labelByEntity = useMemo(() => {
    const m = new Map<string, string>();
    for (const e of entitiesData?.entities ?? []) m.set(e.entity_id, e.label);
    return m;
  }, [entitiesData]);

  /* ----------------------------- Year selection ----------------------------- */
  // Event-year indicators (unit "year": the value IS the year of the event,
  // e.g. legalization or suffrage dates) — the reference year then acts as
  // "by this year", so the map shows every past event instead of a near-empty
  // slice of countries sharing the exact same event year.
  const eventYear = unit === "year";
  const { data: yearData, isLoading: yearLoading } = useYearData(
    indicatorId,
    year,
    sex,
    { byYear: eventYear },
  );

  // Canonical points; if all empty → fall back to the first witness block (flagged inline).
  const canonicalPoints = yearData?.points ?? [];
  const hasCanonicalValues = canonicalPoints.some((p) => p.value !== null);
  const witnessBlocks = yearData?.witness_points ?? [];
  const witnessFallback =
    !hasCanonicalValues && witnessBlocks.length > 0 ? witnessBlocks[0] : null;
  const dataPoints = witnessFallback ? witnessFallback.points : canonicalPoints;

  const colorByEntity = useMemo(() => {
    const values = dataPoints
      .filter((p): p is typeof p & { value: number } => p.value !== null)
      .map((p) => p.value);
    const m = new Map<string, string>();
    for (const p of dataPoints) {
      if (p.value === null) continue;
      m.set(p.entity_id, binColor(percentileOf(p.value, values, higherIsBetter)));
    }
    return m;
  }, [dataPoints, higherIsBetter]);

  const valueByEntity = useMemo(() => {
    const m = new Map<string, number>();
    for (const p of dataPoints) if (p.value !== null) m.set(p.entity_id, p.value);
    return m;
  }, [dataPoints]);

  /** Countries actually carrying a value for the current selection. */
  const nData = valueByEntity.size;

  const canonicalMetaByEntity = useMemo(() => {
    const m = new Map<string, { provider: string; source_ref: string }>();
    for (const p of canonicalPoints) {
      if (!m.has(p.entity_id)) m.set(p.entity_id, { provider: p.provider, source_ref: p.source_ref });
    }
    return m;
  }, [canonicalPoints]);

  /* --------------------------------- Shapes --------------------------------- */
  const shapes = useMemo<TopoShape[] | null>(() => {
    if (!topo) return null;
    const fc = feature(
      topo,
      topo.objects.countries as unknown as GeometryCollection,
    ) as unknown as FeatureCollection<Geometry, GeoJsonProperties>;
    const projection = geoNaturalEarth1().fitExtent(
      [
        [8, 8],
        [MAP_W - 8, MAP_H - 8],
      ],
      fc,
    );
    const path = geoPath(projection);
    return fc.features.map((f, i) => ({
      key: String(f.id ?? i),
      d: path(f) ?? "",
      numericId: String(f.id ?? ""),
      topoName: (f.properties as { name?: string } | null)?.name ?? "",
    }));
  }, [topo]);

  interface HoverState {
    shape: TopoShape;
    x: number;
    y: number;
    left: number;
  }
  const [hover, setHover] = useState<HoverState | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const resolve = (shape: TopoShape) => {
    const iso3 = numericToIso3?.get(shape.numericId) ?? null;
    const entityId = iso3 ? (iso3ToEntity.get(iso3) ?? null) : null;
    const value = entityId ? (valueByEntity.get(entityId) ?? null) : null;
    return {
      iso3,
      entityId,
      label: entityId ? entityLabel(entityId, labelByEntity.get(entityId)) : shape.topoName,
      value,
      color: entityId ? (colorByEntity.get(entityId) ?? null) : null,
      meta: entityId ? (canonicalMetaByEntity.get(entityId) ?? null) : null,
    };
  };

  const hoverInfo = hover ? { shape: hover.shape, resolved: resolve(hover.shape) } : null;

  const onMove = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!e.target || !(e.target instanceof SVGPathElement)) return;
    const key = e.target.getAttribute("data-shape-key");
    if (!key || !shapes) return;
    const shape = shapes.find((s) => s.key === key);
    if (!shape) return;
    const rect = containerRef.current?.getBoundingClientRect();
    const x = e.clientX - (rect?.left ?? 0);
    const y = e.clientY - (rect?.top ?? 0);
    // Clamp here (event handler) rather than in render: refs must not be read while rendering.
    const width = containerRef.current?.clientWidth ?? MAP_W;
    setHover({ shape, x, y, left: Math.min(Math.max(x + 14, 8), width - 180) });
  };

  const tooltipLeft = hover?.left ?? 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex flex-wrap items-center gap-2 font-serif-display text-lg">
          {t((d) => d.indicators.mapTitle)}
          {witnessFallback && (
            <Badge
              variant="outline"
              className="border-witness/50 font-normal text-muted-foreground"
              title={witnessFallback.root_label}
            >
              {t((d) => d.common.basedOnWitness)} · {witnessFallback.root_label}
            </Badge>
          )}
        </CardTitle>
        {sexSplit && (
          <CardAction>
            <SexToggle value={sex} onChange={onSexChange} />
          </CardAction>
        )}
      </CardHeader>
      <CardContent>
        {!shapes ? (
          <Skeleton className="aspect-[780/420] w-full rounded-lg" />
        ) : (
          <div ref={containerRef} className="relative">
            <svg
              viewBox={`0 0 ${MAP_W} ${MAP_H}`}
              className="h-auto w-full"
              role="img"
              aria-label={t((d) => d.indicators.mapTitle)}
              onMouseMove={onMove}
              onMouseLeave={() => setHover(null)}
            >
              {shapes.map((shape) => {
                const { entityId, color, value } = resolve(shape);
                const clickable = Boolean(entityId);
                const isFocus = Boolean(entityId) && entityId === focusEntityId;
                return (
                  <path
                    key={shape.key}
                    data-shape-key={shape.key}
                    d={shape.d}
                    fill={color ?? "var(--muted)"}
                    stroke={isFocus ? "var(--foreground)" : "var(--background)"}
                    strokeWidth={
                      isFocus ? 1.6 : hover?.shape.key === shape.key ? 1.2 : 0.5
                    }
                    className={cn(
                      "transition-[filter]",
                      clickable && "cursor-pointer hover:brightness-90",
                      value === null && !isFocus && "opacity-60",
                    )}
                    onClick={() => {
                      if (entityId) router.push(`/countries/${entityId}`);
                    }}
                  />
                );
              })}
            </svg>
            {hover && hoverInfo && (
              <div
                className="pointer-events-none absolute z-10 max-w-64 rounded-lg border bg-popover px-3 py-2 text-xs shadow-md"
                style={{ left: tooltipLeft, top: hover.y + 14 }}
              >
                <div className="mb-1 font-semibold">{hoverInfo.resolved.label}</div>
                {hoverInfo.resolved.value !== null ? (
                  <div className="tnum">
                    {fmtNumber(hoverInfo.resolved.value, unit, lang)}{" "}
                    <span className="text-muted-foreground">{unitLabel(unit)}</span>
                  </div>
                ) : (
                  <div className="text-muted-foreground">{t((d) => d.indicators.mapNoData)}</div>
                )}
                {witnessFallback ? (
                  <div className="mt-1 text-muted-foreground">
                    {t((d) => d.common.witness)} · {witnessFallback.root_label}
                  </div>
                ) : hoverInfo.resolved.meta ? (
                  <div className="mt-1 truncate text-muted-foreground" title={hoverInfo.resolved.meta.source_ref}>
                    {hoverInfo.resolved.meta.provider} · {hoverInfo.resolved.meta.source_ref}
                  </div>
                ) : null}
              </div>
            )}
          </div>
        )}

        <div className="mt-5 space-y-4">
          {yearLoading && shapes ? (
            <div className="h-5" aria-hidden />
          ) : null}
          <YearSlider
            years={availableYears}
            value={year}
            onChange={onYearChange}
            className={cn(year === null && "opacity-50")}
          />
          {eventYear ? (
            <p className="text-xs text-muted-foreground">
              {t((d) => d.indicators.mapEventNote).replace(
                "{year}",
                String(year ?? ""),
              )}
            </p>
          ) : nData > 0 && nData < 10 ? (
            <p className="text-xs text-amber-700 dark:text-amber-400">
              {t((d) => d.indicators.mapSparse).replace("{n}", String(nData))}
            </p>
          ) : null}
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted-foreground">
            <span className="inline-flex items-center gap-2">
              {t((d) => d.indicators.mapLegendBest)}
              <span
                aria-hidden
                className="flex h-2.5 w-40 overflow-hidden rounded-full"
              >
                {BIN_COLORS_BEST_TO_WORST.map((c) => (
                  <span key={c} className="h-full flex-1" style={{ background: c }} />
                ))}
              </span>
              {t((d) => d.indicators.mapLegendWorst)}
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span
                aria-hidden
                className="h-2.5 w-2.5 rounded-sm"
                style={{ background: "var(--muted)" }}
              />
              {t((d) => d.indicators.mapNoData)}
            </span>
            <Badge variant="secondary" className="tnum font-normal">
              {nData === 1
                ? t((d) => d.indicators.mapCoverageOne)
                : t((d) => d.indicators.mapCoverage).replace("{n}", String(nData))}
            </Badge>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
