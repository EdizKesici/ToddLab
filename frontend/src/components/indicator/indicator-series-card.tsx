"use client";

import { useMemo, useState } from "react";
import {
  Brush,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  type TooltipProps,
} from "recharts";
import { EntityPicker } from "@/components/shared/entity-picker";
import { ChartTooltipShell, colorForSeries } from "@/components/shared/charts";
import { SexToggle, type SexChoice } from "@/components/shared/sex-toggle";
import { EmptyBlock, SkeletonRows } from "@/components/shared/states";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { useEntities, useSeries } from "@/lib/toddlab/client";
import { fmtIndex, fmtNumber, fmtTick } from "@/lib/toddlab/format";
import {
  interpolate,
  useEntityLabel,
  useI18n,
  useUnitLabel,
} from "@/lib/toddlab/i18n";

type ChartRow = { year: number } & Record<string, number | null>;

/** Below this many observed years, a zoom window adds clutter, not value. */
const BRUSH_MIN_ROWS = 24;

interface LineDef {
  key: string;
  color: string;
  dashed: boolean;
  witness: boolean;
  entityId: string;
  sex?: "male" | "female";
  /** Dimmed lines = unsexed totals shown beside sex-split lines. */
  opacity?: number;
}

interface PointMeta {
  provider: string;
  source_ref: string;
  citation?: string;
}

export interface IndicatorSeriesCardProps {
  indicatorId: string;
  sexSplit: boolean;
  unit: string;
  /** Controlled selection — lives in the page URL (use-indicator-query-state). */
  countries: string[];
  onCountriesChange: (countries: string[]) => void;
  sex: SexChoice;
  onSexChange: (sex: SexChoice) => void;
  showWitness: boolean;
  onWitnessChange: (show: boolean) => void;
  /** Base-100 index of the series (already clamped off for unit="year"). */
  base100: boolean;
  onBase100Change: (on: boolean) => void;
}

export function IndicatorSeriesCard({
  indicatorId,
  sexSplit,
  unit,
  countries,
  onCountriesChange,
  sex,
  onSexChange,
  showWitness,
  onWitnessChange,
  base100,
  onBase100Change,
}: IndicatorSeriesCardProps) {
  const { t, lang } = useI18n();
  const entityLabel = useEntityLabel();
  const unitLabel = useUnitLabel();

  const { data, isLoading } = useSeries(indicatorId, countries);
  const { data: entitiesData } = useEntities();

  // X-axis zoom window (data indices) — transient inspection, deliberately
  // not in the URL: a reading gesture, not a data view. The window carries
  // the row count it was drawn on and self-invalidates when the data shape
  // changes (countries, estimates, indicator) — no effect needed.
  const [zoom, setZoom] = useState<{
    start: number;
    end: number;
    len: number;
  } | null>(null);

  const labelById = useMemo(() => {
    const m = new Map<string, string>();
    for (const e of entitiesData?.entities ?? []) m.set(e.entity_id, e.label);
    return m;
  }, [entitiesData]);

  const { rows, lines, metaByKey, rawByKey, baseYear } = useMemo(() => {
    const rowMap = new Map<number, ChartRow>();
    const metaMap = new Map<string, PointMeta>();
    const rawMap = new Map<string, number | null>();
    const lineDefs: LineDef[] = [];

    const yearOf = (y: number): ChartRow => {
      let row = rowMap.get(y);
      if (!row) {
        row = { year: y };
        rowMap.set(y, row);
      }
      return row;
    };

    const keyFor = (prefix: "c" | "w", eid: string, pointSex: "male" | "female" | undefined) => {
      if (sexSplit) {
        // sex=all → sex-tagged points get their own keys, unsexed totals keep the base key.
        if (sex === "all") return pointSex ? `${prefix}:${eid}:${pointSex}` : `${prefix}:${eid}`;
        return pointSex === sex ? `${prefix}:${eid}` : null;
      }
      if (sex !== "all" && pointSex && pointSex !== sex) return null;
      return `${prefix}:${eid}`;
    };

    for (const p of data?.canonical ?? []) {
      if (!countries.includes(p.entity_id)) continue;
      const key = keyFor("c", p.entity_id, p.sex);
      if (!key) continue;
      const row = yearOf(p.year);
      row[key] = p.value;
      rawMap.set(`${key}@${p.year}`, p.value);
      if (!metaMap.has(`${key}@${p.year}`)) {
        metaMap.set(`${key}@${p.year}`, {
          provider: p.provider,
          source_ref: p.source_ref,
          citation: p.citation,
        });
      }
    }

    if (showWitness) {
      for (const block of data?.witnesses ?? []) {
        for (const p of block.points) {
          if (!countries.includes(p.entity_id)) continue;
          const key = keyFor("w", p.entity_id, p.sex);
          if (!key) continue;
          // Never overwrite a canonical cell — witnesses are shown beside, not merged.
          const row = yearOf(p.year);
          if (row[key] === undefined || row[key] === null) {
            row[key] = p.value;
            rawMap.set(`${key}@${p.year}`, p.value);
          }
          if (!metaMap.has(`${key}@${p.year}`)) {
            metaMap.set(`${key}@${p.year}`, {
              provider: block.provider,
              source_ref: block.source_ref,
              citation: block.citation,
            });
          }
        }
      }
    }

    // Sex availability per tier/entity: decide M/F lines vs a single total line.
    const canonicalSexed = new Set(
      (data?.canonical ?? []).filter((p) => p.sex).map((p) => p.entity_id),
    );
    const canonicalUnsexed = new Set(
      (data?.canonical ?? []).filter((p) => !p.sex).map((p) => p.entity_id),
    );
    const witnessSexed = new Set(
      (data?.witnesses ?? []).flatMap((b) => b.points).filter((p) => p.sex).map((p) => p.entity_id),
    );
    const witnessUnsexed = new Set(
      (data?.witnesses ?? []).flatMap((b) => b.points).filter((p) => !p.sex).map((p) => p.entity_id),
    );

    countries.forEach((eid, i) => {
      const color = colorForSeries(i);
      const splitView = sexSplit && sex === "all";

      if (splitView && canonicalSexed.has(eid)) {
        lineDefs.push({ key: `c:${eid}:male`, color, dashed: false, witness: false, entityId: eid, sex: "male" });
        lineDefs.push({ key: `c:${eid}:female`, color, dashed: true, witness: false, entityId: eid, sex: "female" });
        if (canonicalUnsexed.has(eid)) {
          lineDefs.push({ key: `c:${eid}`, color, dashed: false, witness: false, entityId: eid, opacity: 0.35 });
        }
      } else {
        lineDefs.push({ key: `c:${eid}`, color, dashed: false, witness: false, entityId: eid });
      }

      if (showWitness) {
        if (splitView && witnessSexed.has(eid)) {
          lineDefs.push({ key: `w:${eid}:male`, color, dashed: true, witness: true, entityId: eid, sex: "male" });
          lineDefs.push({ key: `w:${eid}:female`, color, dashed: true, witness: true, entityId: eid, sex: "female" });
          if (witnessUnsexed.has(eid)) {
            lineDefs.push({ key: `w:${eid}`, color, dashed: true, witness: true, entityId: eid, opacity: 0.35 });
          }
        } else {
          lineDefs.push({ key: `w:${eid}`, color, dashed: true, witness: true, entityId: eid });
        }
      }
    });

    const rowsSorted = [...rowMap.values()].sort((a, b) => a.year - b.year);

    // Base-100 index: the baseline is the FIRST year where every canonical
    // line on the chart has a value. One shared base keeps trajectories
    // comparable — per-series bases would compare different start years.
    const canonicalKeys = lineDefs.filter((l) => !l.witness).map((l) => l.key);
    let baseYear: number | null = null;
    if (base100 && canonicalKeys.length > 0) {
      for (const row of rowsSorted) {
        if (canonicalKeys.every((k) => typeof row[k] === "number")) {
          baseYear = row.year;
          break;
        }
      }
    }

    let chartRows = rowsSorted;
    let chartLines = lineDefs;
    if (base100 && baseYear !== null) {
      const baseRow = rowsSorted.find((r) => r.year === baseYear) as ChartRow;
      const denomByKey = new Map<string, number>();
      const kept: LineDef[] = [];
      for (const l of lineDefs) {
        // Witness lines inherit the denominator of their official twin;
        // without one they are hidden rather than indexed on a mixed base.
        const denom = baseRow[l.witness ? l.key.replace(/^w:/, "c:") : l.key];
        if (typeof denom === "number" && denom !== 0) {
          denomByKey.set(l.key, denom);
          kept.push(l);
        }
      }
      chartLines = kept;
      chartRows = rowsSorted.map((row) => {
        const next: ChartRow = { year: row.year };
        for (const [key, denom] of denomByKey) {
          const v = row[key];
          // Explicit gaps (null) stay null — never interpolated, never zeroed.
          if (typeof v === "number") next[key] = (v / denom) * 100;
        }
        return next;
      });
    }

    return {
      rows: chartRows,
      lines: chartLines,
      metaByKey: metaMap,
      rawByKey: rawMap,
      baseYear: base100 ? baseYear : null,
    };
  }, [data, countries, sex, sexSplit, showWitness, base100]);

  const lineByKey = useMemo(() => new Map(lines.map((l) => [l.key, l])), [lines]);

  const indexing = base100 && baseYear !== null;

  const zoomStart =
    zoom && zoom.len === rows.length
      ? Math.min(zoom.start, rows.length - 1)
      : undefined;
  const zoomEnd =
    zoom && zoom.len === rows.length
      ? Math.min(zoom.end, rows.length - 1)
      : undefined;
  const zoomed =
    zoomStart !== undefined &&
    zoomEnd !== undefined &&
    (zoomStart > 0 || zoomEnd < rows.length - 1);

  const labelOf = (eid: string) => entityLabel(eid, labelById.get(eid));

  const sexSuffix = (s: LineDef["sex"]) => {
    if (!s) return "";
    return s === "male" ? ` · ${t((d) => d.common.male)}` : ` · ${t((d) => d.common.female)}`;
  };

  const renderTooltip = (props: TooltipProps<number, string>) => {
    const { active, payload, label } = props;
    if (!active || !payload || payload.length === 0) return null;
    const chartRows = payload
      .map((entry) => {
        const key = String(entry.dataKey ?? "");
        const def = lineByKey.get(key);
        if (!def) return null;
        const value = Array.isArray(entry.value) ? entry.value[0] : entry.value;
        const meta = metaByKey.get(`${key}@${Number(label)}`);
        const raw = rawByKey.get(`${key}@${Number(label)}`);
        return {
          label: `${entityLabel(def.entityId, labelById.get(def.entityId))}${sexSuffix(def.sex)}${def.witness ? ` · ${t((d) => d.common.witness)}` : ""}`,
          value: indexing ? fmtIndex(value, lang) : fmtNumber(value, unit, lang),
          // In index mode the raw figure travels beside the label so the
          // sourced number never disappears behind the transformation.
          raw: indexing && typeof raw === "number" ? raw : null,
          color: def.color,
          dashed: def.dashed,
          meta,
        };
      })
      .filter((r): r is NonNullable<typeof r> => r !== null);
    if (chartRows.length === 0) return null;
    return (
      <ChartTooltipShell
        title={<span className="tnum">{label}</span>}
        rows={chartRows.map((r) => ({
          label: (
            <span
              title={
                r.meta
                  ? `${r.meta.provider} · ${r.meta.source_ref}${r.meta.citation ? ` · ${r.meta.citation}` : ""}`
                  : undefined
              }
            >
              {r.label}
              {r.raw !== null && (
                <span className="text-muted-foreground/70">
                  {" · "}
                  {fmtNumber(r.raw, unit, lang)}
                </span>
              )}
            </span>
          ),
          value: r.value,
          color: r.color,
          dashed: r.dashed,
        }))}
      />
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="font-serif-display text-lg">
          {t((d) => d.indicators.seriesTitle)}
        </CardTitle>
        <CardDescription>{t((d) => d.indicators.seriesPick)}</CardDescription>
        <CardAction className="flex flex-wrap items-center gap-3">
          {sexSplit && <SexToggle value={sex} onChange={onSexChange} />}
          <div className="flex items-center gap-1.5">
            <Switch
              id={`witness-${indicatorId}`}
              checked={showWitness}
              onCheckedChange={onWitnessChange}
              aria-label={t((d) => d.common.witness)}
            />
            <Label
              htmlFor={`witness-${indicatorId}`}
              className="text-xs text-muted-foreground"
            >
              {t((d) => d.common.witness)}
            </Label>
          </div>
          {unit !== "year" && (
            <div className="flex items-center gap-1.5">
              <Switch
                id={`base100-${indicatorId}`}
                checked={base100}
                onCheckedChange={onBase100Change}
                aria-label={t((d) => d.indicators.base100)}
              />
              <Label
                htmlFor={`base100-${indicatorId}`}
                className="text-xs text-muted-foreground"
              >
                {t((d) => d.indicators.base100)}
              </Label>
            </div>
          )}
        </CardAction>
      </CardHeader>
      <CardContent className="space-y-4">
        <EntityPicker selected={countries} onChange={onCountriesChange} max={6} />

        {isLoading ? (
          <SkeletonRows rows={6} className="h-72" />
        ) : countries.length === 0 || rows.length === 0 ? (
          <EmptyBlock
            message={
              countries.length === 0
                ? t((d) => d.compare.pickCountriesFirst)
                : t((d) => d.common.noData)
            }
          />
        ) : (
          <>
            {base100 && !indexing ? (
              <div className="rounded-md border border-amber-500/40 bg-amber-500/5 px-3 py-2.5 text-xs text-amber-700 dark:text-amber-400">
                {t((d) => d.indicators.base100Unavailable)}
              </div>
            ) : (
              <div className="h-72 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={rows}
                    margin={{ top: 8, right: 12, bottom: 0, left: 0 }}
                  >
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="var(--border)"
                      vertical={false}
                    />
                    <XAxis
                      dataKey="year"
                      type="number"
                      domain={["dataMin", "dataMax"]}
                      allowDecimals={false}
                      tick={{ fontSize: 11 }}
                      tickFormatter={(v: number) => String(Math.round(v))}
                      stroke="var(--muted-foreground)"
                      tickLine={false}
                    />
                    <YAxis
                      width={48}
                      tick={{ fontSize: 11 }}
                      tickFormatter={(v: number) =>
                        indexing ? fmtTick(v, "") : fmtTick(v, unit)
                      }
                      stroke="var(--muted-foreground)"
                      tickLine={false}
                    />
                    <Tooltip content={renderTooltip} cursor={{ stroke: "var(--border)" }} />
                    {rows.length >= BRUSH_MIN_ROWS && (
                      <Brush
                        dataKey="year"
                        height={30}
                        travellerWidth={16}
                        strokeWidth={1}
                        stroke="var(--primary)"
                        fill="var(--muted)"
                        startIndex={zoomStart}
                        endIndex={zoomEnd}
                        tickFormatter={(v: number) => String(Math.round(v))}
                        onChange={(
                          range: { startIndex?: number; endIndex?: number },
                        ) => {
                          if (
                            typeof range.startIndex === "number" &&
                            typeof range.endIndex === "number"
                          ) {
                            setZoom({
                              start: range.startIndex,
                              end: range.endIndex,
                              len: rows.length,
                            });
                          }
                        }}
                      />
                    )}
                    {lines.map((l) => (
                      <Line
                        key={l.key}
                        type="monotone"
                        dataKey={l.key}
                        stroke={l.color}
                        strokeWidth={l.witness ? 1.75 : 2}
                        strokeOpacity={l.opacity ?? (l.witness ? 0.9 : 1)}
                        // Estimates keep their country color but use a fine dot
                        // pattern — never merged with the official line style.
                        strokeDasharray={l.witness ? "2 4" : l.dashed ? "5 3" : undefined}
                        connectNulls={false}
                        dot={false}
                        activeDot={{ r: 3 }}
                        isAnimationActive={false}
                      />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}

            <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs">
              {countries.map((eid, i) => (
                <span key={eid} className="inline-flex items-center gap-1.5">
                  <span
                    aria-hidden
                    className="h-2.5 w-2.5 rounded-sm"
                    style={{ background: colorForSeries(i) }}
                  />
                  {entityLabel(eid, labelById.get(eid))}
                </span>
              ))}
              {sexSplit && sex === "all" && (
                <span className="inline-flex items-center gap-1.5 text-muted-foreground">
                  <span
                    aria-hidden
                    className="inline-block h-0 w-5 border-t-2 border-foreground"
                  />
                  {t((d) => d.common.male)}
                  <span aria-hidden className="text-muted-foreground/60">/</span>
                  <span
                    aria-hidden
                    className="inline-block h-0 w-5 border-t-2 border-dashed border-foreground"
                  />
                  {t((d) => d.common.female)}
                </span>
              )}
              {showWitness && (
                <span className="inline-flex items-center gap-1.5 text-muted-foreground">
                  <span
                    aria-hidden
                    className="inline-block h-0 w-5 border-t-2 border-dotted border-foreground"
                  />
                  {t((d) => d.common.witness)}
                </span>
              )}
            </div>
            {zoomed && (
              <button
                type="button"
                onClick={() =>
                  // Explicit full window — passing undefined would leave
                  // Recharts' internal brush state zoomed.
                  setZoom({ start: 0, end: rows.length - 1, len: rows.length })
                }
                className="self-start text-xs text-muted-foreground underline-offset-2 transition-colors hover:text-foreground hover:underline"
              >
                {t((d) => d.indicators.resetZoom)}
              </button>
            )}
            {indexing && (
              <p className="text-xs text-muted-foreground">
                {interpolate(t((d) => d.indicators.base100Note), {
                  year: String(baseYear),
                })}
              </p>
            )}
            <p className="text-xs text-muted-foreground">
              {t((d) => d.common.gapNote)}
            </p>
          </>
        )}
      </CardContent>
    </Card>
  );
}
