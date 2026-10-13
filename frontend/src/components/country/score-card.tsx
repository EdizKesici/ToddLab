"use client";

import * as React from "react";
import { CalendarClock, ChevronDown, Scale, Sparkles } from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ChartTooltipShell } from "@/components/shared/charts";
import { ScoreComponentsList } from "./score-components-list";
import { ScoreDeltaPanel } from "./score-delta-panel";
import { ScoreWeightsPanel } from "./score-weights-panel";
import { interpolate, useIndicatorLabel, useI18n } from "@/lib/toddlab/i18n";
import type { Dictionary } from "@/lib/toddlab/i18n/dictionaries";
import {
  useScoreEntity,
  useScoreMeta,
  type ScoreEntityComponent,
  type ScoreEntitySide,
} from "@/lib/toddlab/client";
import { fmtCoverage, fmtPct1, fmtScore } from "@/lib/toddlab/format";
import {
  scoreAtYear,
  type ScoreCompSeries,
} from "@/lib/toddlab/score-core";
import type { ScoreName } from "@/lib/toddlab/score-types";
import { cn } from "@/lib/utils";

type PresetChoice = "equal" | "todd" | "custom";

function weightsOf(side: ScoreEntitySide, preset: "equal" | "todd"): Record<string, number> {
  const out: Record<string, number> = {};
  for (const c of side.components) {
    out[c.key] = preset === "todd" ? c.weight_todd : c.weight_equal;
  }
  return out;
}

export function ScoreCard({ entityId }: { entityId: string }) {
  const { t, lang } = useI18n();
  const indicatorLabel = useIndicatorLabel();
  const entity = useScoreEntity(entityId);
  const meta = useScoreMeta();

  const sides = entity.data;
  const availableScores = React.useMemo<ScoreName[]>(() => {
    if (!sides) return [];
    if (sides.official && sides.modelled) return ["official", "modelled"];
    if (sides.official) return ["official"];
    if (sides.modelled) return ["modelled"];
    return [];
  }, [sides]);

  const [scoreName, setScoreName] = React.useState<ScoreName | null>(null);
  const effectiveScore: ScoreName | null =
    scoreName && availableScores.includes(scoreName)
      ? scoreName
      : (availableScores[0] ?? null);
  const side = sides
    ? effectiveScore === "official"
      ? sides.official
      : sides.modelled
    : null;

  const [preset, setPreset] = React.useState<PresetChoice>("equal");
  const [lastBasePreset, setLastBasePreset] = React.useState<"equal" | "todd">("equal");
  const [customWeights, setCustomWeights] = React.useState<Record<string, number> | null>(null);
  const [year, setYear] = React.useState<number | null>(null);
  const [showComponents, setShowComponents] = React.useState(false);

  const threshold = meta.data?.global.coverage_threshold ?? 0.6;
  const minCommon = meta.data?.global.delta_min_common_weight ?? 0.5;

  const years = side?.years ?? [];
  const effectiveYear =
    year !== null && years.includes(year) ? year : (years[years.length - 1] ?? null);

  const weightsByKey = React.useMemo(() => {
    if (!side) return {} as Record<string, number>;
    if (preset === "custom") return customWeights ?? weightsOf(side, lastBasePreset);
    return weightsOf(side, preset);
  }, [side, preset, customWeights, lastBasePreset]);

  const comps = React.useMemo<ScoreCompSeries[]>(
    () =>
      side
        ? side.components.map((c) => ({
            key: c.key,
            weight: weightsByKey[c.key] ?? 0,
            normalised: c.normalised,
            age: c.age,
          }))
        : [],
    [side, weightsByKey],
  );

  const atYear = React.useMemo(
    () =>
      effectiveYear !== null
        ? scoreAtYear(comps, effectiveYear, { coverageThreshold: threshold })
        : null,
    [comps, effectiveYear, threshold],
  );

  const chartData = React.useMemo(
    () =>
      years.map((y) => {
        const r = scoreAtYear(comps, y, { coverageThreshold: threshold });
        return {
          year: y,
          score: r?.emitted ? r.score : null,
          coverage: r?.coverage ?? null,
          n: r?.n ?? 0,
        };
      }),
    [years, comps, threshold],
  );

  const totalComponents = comps.length;

  // Carried share at the selected year (share of available values resting on
  // an observation older than the year itself).
  const carriedAtYear = React.useMemo(() => {
    if (!atYear || atYear.n === 0) return null;
    const yearNum = effectiveYear ?? 0;
    let carried = 0;
    for (const c of comps) {
      if (c.normalised[String(yearNum)] !== undefined && (c.age[String(yearNum)] ?? 0) >= 1) {
        carried++;
      }
    }
    return carried / atYear.n;
  }, [atYear, comps, effectiveYear]);

  const compByKey = React.useMemo(
    () => new Map(side?.components.map((c) => [c.key, c]) ?? []),
    [side],
  );

  const labelOfKey = React.useCallback(
    (key: string) => {
      const c = compByKey.get(key);
      if (!c) return key;
      return compLabel(c, indicatorLabel, t);
    },
    [compByKey, indicatorLabel, t],
  );

  /* ------------------------------- Loading ------------------------------- */

  if (entity.isLoading) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <Skeleton className="h-5 w-56" />
        </CardHeader>
        <CardContent className="space-y-3">
          <Skeleton className="h-12 w-64" />
          <Skeleton className="h-28 w-full" />
        </CardContent>
      </Card>
    );
  }

  /* ----------------------------- Not scored ------------------------------ */

  if (entity.isError || !sides || availableScores.length === 0) {
    if (entity.isError && (entity.error as Error & { status?: number })?.status !== 404) {
      return null; // silent: the score card must never break the profile page
    }
    return (
      <Card>
        <CardContent className="flex flex-col gap-1.5 p-6">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-muted-foreground" />
            <h3 className="font-serif-display text-lg font-semibold tracking-tight">
              {t((d) => d.score.title)}
            </h3>
          </div>
          <p className="text-sm text-muted-foreground">{t((d) => d.score.noScoreEntity)}</p>
          <p className="text-xs text-muted-foreground">{t((d) => d.score.noScoreEntityWhy)}</p>
        </CardContent>
      </Card>
    );
  }

  const switchScore = (s: ScoreName) => {
    setScoreName(s);
    setYear(null);
    if (preset === "custom") {
      const target = s === "official" ? sides.official : sides.modelled;
      setCustomWeights(target ? weightsOf(target, lastBasePreset) : null);
    }
  };

  const switchPreset = (p: PresetChoice) => {
    if (p === "custom" && preset !== "custom") {
      setCustomWeights(weightsByKey);
    }
    if (p !== "custom") setLastBasePreset(p);
    setPreset(p);
  };

  const emitted = atYear?.emitted ?? false;
  const belowThreshold =
    atYear !== null && !emitted && atYear.coverage < threshold;

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex flex-col gap-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex flex-wrap items-center gap-2">
              <Scale className="h-4 w-4 text-primary" aria-hidden />
              <h3 className="font-serif-display text-lg font-semibold tracking-tight">
                {t((d) => d.score.title)}
              </h3>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {availableScores.length > 1 && (
                <SegmentedMini
                  ariaLabel={t((d) => d.score.title)}
                  value={effectiveScore as ScoreName}
                  onChange={switchScore}
                  options={[
                    { value: "official", label: t((d) => d.score.official) },
                    { value: "modelled", label: t((d) => d.score.modelled) },
                  ]}
                />
              )}
              <SegmentedMini
                ariaLabel={t((d) => d.score.preset)}
                value={preset}
                onChange={(p) => switchPreset(p as PresetChoice)}
                options={[
                  { value: "equal", label: t((d) => d.score.presetEqual) },
                  { value: "todd", label: t((d) => d.score.presetTodd) },
                  { value: "custom", label: t((d) => d.score.presetCustom) },
                ]}
              />
            </div>
          </div>

          <p className="max-w-3xl text-xs leading-relaxed text-muted-foreground">
            {effectiveScore === "official"
              ? t((d) => d.score.officialHint)
              : t((d) => d.score.modelledHint)}{" "}
            {preset === "custom"
              ? t((d) => d.score.customNote)
              : t((d) => d.score.presetsExplained)}
          </p>
        </div>
      </CardHeader>

      <CardContent className="space-y-5">
        {/* Score + year */}
        <div className="grid gap-5 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
          <div className="min-w-0 space-y-3">
            {effectiveYear !== null && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <CalendarClock className="h-3.5 w-3.5" aria-hidden />
                <span className="tnum font-medium text-foreground">{effectiveYear}</span>
                {carriedAtYear !== null && carriedAtYear > 0 && (
                  <Badge
                    variant="outline"
                    className="border-amber-600/40 bg-amber-600/10 font-normal text-amber-700 dark:text-amber-400"
                  >
                    {interpolate(t((d) => d.score.carriedShare), {
                      p: fmtPct1(carriedAtYear, lang),
                    })}
                  </Badge>
                )}
              </div>
            )}

            {atYear && emitted ? (
              <div className="flex flex-wrap items-end gap-x-4 gap-y-1">
                <div className="tnum font-serif-display text-5xl font-semibold leading-none tracking-tight">
                  {fmtScore(atYear.score, lang)}
                  <span className="ml-1 align-middle text-base font-normal text-muted-foreground">
                    /100
                  </span>
                </div>
                <div className="space-y-0.5 pb-1 text-xs text-muted-foreground">
                  <div>
                    {t((d) => d.score.coverage)} :{" "}
                    <span className="tnum font-medium text-foreground">
                      {fmtCoverage(atYear.coverage, lang)}
                    </span>
                  </div>
                  <div className="tnum">
                    {atYear.n}/{totalComponents} {t((d) => d.score.components)}
                  </div>
                </div>
              </div>
            ) : (
              <div
                role="note"
                className="rounded-lg border border-amber-500/40 bg-amber-500/5 px-4 py-3 text-sm text-amber-800 dark:text-amber-300"
              >
                <div className="font-medium">{t((d) => d.score.notEmitted)}</div>
                <div className="mt-0.5 text-xs">
                  {belowThreshold && atYear
                    ? interpolate(t((d) => d.score.notEmittedCoverage), {
                        p: fmtPct1(atYear.coverage, lang),
                        t: String(Math.round(threshold * 100)),
                      })
                    : atYear
                      ? t((d) => d.score.notEmittedGhost)
                      : t((d) => d.common.noData)}
                </div>
              </div>
            )}

            {/* Score over time */}
            <div>
              <div className="mb-1 flex items-baseline justify-between">
                <h4 className="text-sm font-medium">{t((d) => d.score.scoreChart)}</h4>
                <span className="text-[11px] text-muted-foreground">
                  {t((d) => d.score.scoreChartHint)}
                </span>
              </div>
              <div className="h-36">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData} margin={{ top: 6, right: 8, bottom: 0, left: -18 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                    <XAxis
                      dataKey="year"
                      type="number"
                      domain={["dataMin", "dataMax"]}
                      tick={{ fontSize: 11 }}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(v: number) => String(v)}
                    />
                    <YAxis
                      domain={[0, 100]}
                      ticks={[0, 25, 50, 75, 100]}
                      tick={{ fontSize: 11 }}
                      tickLine={false}
                      axisLine={false}
                    />
                    <Tooltip
                      cursor={{ stroke: "var(--border)" }}
                      content={({ active, payload, label }) => {
                        if (!active || !payload || payload.length === 0) return null;
                        const row = payload[0].payload as {
                          year: number;
                          coverage: number | null;
                          n: number;
                        };
                        return (
                          <ChartTooltipShell
                            title={String(label)}
                            rows={[
                              {
                                label: t((d) => d.score.tableScore),
                                value: fmtScore(payload[0].value as number, lang),
                                color: "var(--chart-1)",
                              },
                              {
                                label: t((d) => d.score.coverage),
                                value: fmtCoverage(row.coverage, lang),
                              },
                              {
                                label: t((d) => d.score.components),
                                value: `${row.n}/${totalComponents}`,
                              },
                            ]}
                          />
                        );
                      }}
                    />
                    <Line
                      type="monotone"
                      dataKey="score"
                      stroke="var(--chart-1)"
                      strokeWidth={2}
                      connectNulls={false}
                      dot={{ r: 2.5, fill: "var(--chart-1)", strokeWidth: 0 }}
                      activeDot={{ r: 4 }}
                      isAnimationActive={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Tabs */}
          <Tabs defaultValue="delta" className="min-w-0 gap-3">
            <TabsList className="w-full justify-start overflow-x-auto">
              <TabsTrigger value="delta">{t((d) => d.score.deltaTitle)}</TabsTrigger>
              <TabsTrigger value="weights">{t((d) => d.score.weightsTitle)}</TabsTrigger>
            </TabsList>
            <TabsContent value="delta">
              <ScoreDeltaPanel
                comps={comps}
                years={years}
                minCommonWeight={minCommon}
                labelOf={labelOfKey}
              />
            </TabsContent>
            <TabsContent value="weights">
              <ScoreWeightsPanel
                components={side?.components ?? []}
                weights={weightsByKey}
                onChange={(key, v) => {
                  setCustomWeights((prev) => ({
                    ...(prev ?? weightsByKey),
                    [key]: v,
                  }));
                  // Dragging a slider while a preset is active would snap back
                  // silently (controlled value) — enter custom mode instead.
                  if (preset !== "custom") setPreset("custom");
                }}
                onReset={() =>
                  side && setCustomWeights(weightsOf(side, lastBasePreset))
                }
                totalWeight={Object.values(weightsByKey).reduce((a, b) => a + b, 0)}
              />
            </TabsContent>
          </Tabs>
        </div>

        {/* Component breakdown: collapsed by default, click to expand */}
        <div className="border-t pt-3">
          <button
            type="button"
            onClick={() => setShowComponents((v) => !v)}
            aria-expanded={showComponents}
            className="flex items-center gap-1.5 rounded text-sm font-medium transition-colors hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <ChevronDown
              aria-hidden
              className={cn(
                "h-4 w-4 text-muted-foreground transition-transform",
                showComponents && "rotate-180",
              )}
            />
            {t((d) => d.score.componentList)}
          </button>
          {showComponents && side && effectiveYear !== null && (
            <div className="mt-3">
              <ScoreComponentsList
                components={side.components}
                weights={weightsByKey}
                year={effectiveYear}
                labelOf={(c) => compLabel(c, indicatorLabel, t)}
              />
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

/* ------------------------------ Helpers --------------------------------- */

function compLabel(
  c: ScoreEntityComponent,
  indicatorLabel: (id: string, enLabel: string) => string,
  t: (fn: (d: Dictionary) => string) => string,
): string {
  const base = indicatorLabel(c.indicator, c.label_en);
  if (c.sex === "male") return `${base} ${t((d) => d.score.sexMale)}`;
  if (c.sex === "female") return `${base} ${t((d) => d.score.sexFemale)}`;
  return base;
}

function SegmentedMini<T extends string>({
  value,
  options,
  onChange,
  ariaLabel,
}: {
  value: T;
  options: { value: T; label: string }[];
  onChange: (v: T) => void;
  ariaLabel: string;
}) {
  return (
    <div role="group" aria-label={ariaLabel} className="inline-flex rounded-lg bg-muted p-0.5">
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          aria-pressed={value === o.value}
          onClick={() => onChange(o.value)}
          className={cn(
            "rounded-md px-2.5 py-1 text-xs transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
            value === o.value
              ? "bg-background font-medium text-foreground shadow-xs"
              : "text-muted-foreground hover:text-foreground",
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}
