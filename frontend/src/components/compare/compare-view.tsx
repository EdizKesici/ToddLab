"use client";

/**
 * /compare — the ToddLab comparator.
 *
 * Full state lives in the URL (see use-query-state.ts): countries, metrics,
 * mode (year | period), reference year or period bounds, witness toggle and
 * per-metric sex choice. Layout: sticky control bar → group synthesis
 * (rank heatmap) → one animated card per metric.
 */

import { Suspense, useEffect, useMemo, useState } from "react";
import { useQueries } from "@tanstack/react-query";
import { Info, Sparkles } from "lucide-react";
import { EntityPicker } from "@/components/shared/entity-picker";
import { MetricPicker } from "@/components/shared/metric-picker";
import { PageHeader } from "@/components/shared/page-header";
import { EmptyBlock, ErrorBlock, SkeletonRows } from "@/components/shared/states";
import { YearSlider } from "@/components/shared/year-slider";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { MetricCard } from "@/components/compare/metric-card";
import { SynthesisGrid } from "@/components/compare/synthesis-grid";
import {
  useCompareQueryState,
  COMPARE_DEFAULTS,
  MAX_COUNTRIES,
  MAX_METRICS,
  type CompareMode,
  type CompareQueryState,
} from "@/components/compare/use-query-state";
import type { SexChoice } from "@/components/shared/sex-toggle";
import {
  useCatalog,
  useEntities,
  type SeriesPayload,
} from "@/lib/toddlab/client";
import { interpolate, useI18n } from "@/lib/toddlab/i18n";

/* --------------------------------- Presets --------------------------------- */

type PresetKey =
  | "presetFallFinal"
  | "presetG7"
  | "presetEuBig4"
  | "presetMediterranean"
  | "presetDefeat";

interface Preset {
  key: PresetKey;
  ids: string[];
  /** Scenario presets load the book's scene: metrics + era (mode/year/period). */
  metrics?: string[];
  mode?: CompareMode;
  year?: number;
  from?: number;
  to?: number;
}

const PRESETS: Preset[] = [
  {
    // Todd, "La Chute finale" (1976): the rise of Soviet infant mortality,
    // read against the USA, as the hard signal of the system's collapse.
    // The official Soviet series runs 1970-1990 — hence the period bounds.
    key: "presetFallFinal",
    ids: ["ussr", "united_states"],
    metrics: ["infant_mortality"],
    mode: "period",
    from: 1970,
    to: 1990,
  },
  {
    key: "presetG7",
    ids: [
      "canada",
      "france",
      "germany",
      "italy",
      "japan",
      "united_kingdom",
      "united_states",
    ],
  },
  { key: "presetEuBig4", ids: ["france", "germany", "italy", "poland"] },
  {
    // North shore + Anatolia + south shore + Levant: 12 countries, as many as
    // the comparator allows. Todd's Mediterranean fault line, both banks.
    key: "presetMediterranean",
    ids: [
      "france",
      "spain",
      "italy",
      "greece",
      "turkiye",
      "morocco",
      "algeria",
      "tunisia",
      "libya",
      "egypt",
      "israel",
      "lebanon",
    ],
  },
  {
    // Todd, "La Défaite de l'Occident" (2024): literacy/education and
    // fertility — the two hard signals of the book — since the 1980 plateau.
    key: "presetDefeat",
    ids: [
      "united_states",
      "russian_federation",
      "france",
      "japan",
      "germany",
      "united_kingdom",
    ],
    metrics: ["birth_rate_fertility", "tertiary_education_share"],
    mode: "period",
    from: 1980,
    to: 2024,
  },
];

/* ----------------------- Union of available years ----------------------- */

/**
 * Union of available years across the selected metrics' series, scoped to
 * what the charts actually draw:
 * - official (canonical) years always;
 * - estimation (witness) years only when the estimates toggle is on —
 *   otherwise one long-run estimation series (e.g. French life expectancy
 *   reconstructed back to 1816) would drag the whole slider into decades
 *   where no official data exists.
 * Uses the exact same queryKey as useSeries → React Query dedupes and
 * the metric cards hit the cache, no extra network requests.
 */
function useYearsUnion(
  metricIds: string[],
  countries: string[],
  includeWitness: boolean,
): { years: number[]; canonicalMin: number | null; witnessMin: number | null } {
  const key = [...countries].sort().join(",");
  const queries = useQueries({
    queries: metricIds.map((id) => ({
      queryKey: ["series", id, key],
      queryFn: async (): Promise<SeriesPayload> => {
        const res = await fetch(
          `/api/indicators/${id}/series?countries=${encodeURIComponent(key)}`,
        );
        if (!res.ok) {
          const body = (await res.json().catch(() => ({}))) as {
            error?: string;
          };
          const err = new Error(body.error ?? `HTTP ${res.status}`) as Error & {
            status?: number;
          };
          err.status = res.status;
          throw err;
        }
        return res.json() as Promise<SeriesPayload>;
      },
      enabled: countries.length > 0,
      staleTime: 10 * 60 * 1000,
      retry: (count: number, err: unknown) => {
        const status = (err as Error & { status?: number }).status;
        if (status === 404 || status === 503) return false;
        return count < 2;
      },
    })),
  });

  const set = new Set<number>();
  let canonicalMin: number | null = null;
  let witnessMin: number | null = null;
  for (const q of queries) {
    const d = q.data as SeriesPayload | undefined;
    if (!d) continue;
    for (const p of d.canonical) {
      if (p.value === null) continue;
      set.add(p.year);
      if (canonicalMin === null || p.year < canonicalMin) canonicalMin = p.year;
    }
    if (!includeWitness) continue;
    for (const w of d.witnesses) {
      for (const p of w.points) {
        if (p.value === null) continue;
        set.add(p.year);
        if (witnessMin === null || p.year < witnessMin) witnessMin = p.year;
      }
    }
  }
  return {
    years: [...set].sort((a, b) => a - b),
    canonicalMin,
    witnessMin,
  };
}

/* --------------------------------- The view --------------------------------- */

function CompareView() {
  const { t } = useI18n();
  const { state, patch } = useCompareQueryState();
  const entities = useEntities();
  const catalog = useCatalog();
  const [familyFilter, setFamilyFilter] = useState<string | null>(null);

  const { years, canonicalMin, witnessMin } = useYearsUnion(
    state.metrics,
    state.countries,
    state.showWitness,
  );
  const minYear = years.length > 0 ? years[0] : COMPARE_DEFAULTS.from;
  const maxYear =
    years.length > 0 ? years[years.length - 1] : COMPARE_DEFAULTS.to;

  /* Keep the selected year/period inside the current union: toggling the
     estimates off shrinks the range (long-run estimation years vanish),
     so the stored year/period must snap back to real observed years. */
  const yearsKey = years.join(",");
  useEffect(() => {
    if (!yearsKey) return;
    const list = yearsKey.split(",").map(Number);
    const lo = list[0];
    const hi = list[list.length - 1];
    const nearest = (v: number) =>
      list.reduce((a, b) => (Math.abs(b - v) < Math.abs(a - v) ? b : a), list[0]);
    const p: Partial<CompareQueryState> = {};
    if (!list.includes(state.year)) p.year = nearest(state.year);
    if (state.from < lo) p.from = lo;
    if (state.to > hi) p.to = hi;
    if (Object.keys(p).length > 0) patch(p);
  }, [yearsKey, state.year, state.from, state.to, patch]);

  // The estimates toggle widens the slider into estimation-only decades —
  // say so once, with the year that drives it.
  const showWitnessRangeHint =
    state.showWitness &&
    witnessMin !== null &&
    (canonicalMin === null || witnessMin < canonicalMin);

  const entitySet = useMemo(
    () => new Set((entities.data?.entities ?? []).map((e) => e.entity_id)),
    [entities.data],
  );
  const catalogSet = useMemo(
    () => new Set((catalog.data?.indicators ?? []).map((i) => i.id)),
    [catalog.data],
  );

  const applyPreset = (p: Preset) => {
    // Only keep ids that actually exist in the registries.
    const next: Partial<CompareQueryState> = {
      countries: p.ids.filter((id) => entitySet.has(id)),
    };
    if (p.metrics && p.metrics.length > 0) {
      next.metrics = p.metrics.filter((id) => catalogSet.has(id));
      if (p.mode) next.mode = p.mode;
      if (p.year !== undefined) next.year = p.year;
      if (p.from !== undefined) next.from = p.from;
      if (p.to !== undefined) next.to = p.to;
    }
    patch(next);
  };

  const setSex = (metricId: string, choice: SexChoice) => {
    const next = { ...state.sexChoices };
    if (choice === "all") delete next[metricId];
    else next[metricId] = choice;
    patch({ sexChoices: next });
  };

  const clampYear = (v: number) => Math.min(maxYear, Math.max(minYear, v));

  const globalError = entities.isError || catalog.isError;

  return (
    <div className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6">
      <PageHeader
        title={t((d) => d.compare.title)}
        subtitle={t((d) => d.compare.subtitle)}
      />

      {/* Presets — deliberately OUTSIDE the control frame: they are
          one-click shortcuts, not part of the selection itself. */}
      <div className="mt-6 flex flex-wrap items-center gap-x-3 gap-y-2">
        <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
          <Sparkles className="h-3.5 w-3.5" aria-hidden />
          {t((d) => d.compare.presets)}
        </span>
        {PRESETS.map((p) => (
          <Button
            key={p.key}
            variant="outline"
            size="sm"
            className="h-7 rounded-full border-dashed px-3 text-xs"
            onClick={() => applyPreset(p)}
          >
            {t((d) => d.compare[p.key])}
          </Button>
        ))}
      </div>

      {/* Control bar — sticky right under the 56px site header */}
      <Card className="sticky top-14 z-30 mt-3 gap-0 rounded-xl border bg-card/85 py-4 shadow-sm backdrop-blur-md">
        <CardContent className="space-y-5 px-4 sm:px-5">
          {/* Row 1 — countries */}
          <div className="flex flex-wrap items-center gap-x-4 gap-y-3">
            <span className="w-16 shrink-0 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              {t((d) => d.compare.countries)}
            </span>
            <EntityPicker
              selected={state.countries}
              onChange={(ids) => patch({ countries: ids })}
              max={MAX_COUNTRIES}
            />
          </div>

          {/* Row 2 — metrics + mode + witnesses */}
          <div className="flex flex-wrap items-center gap-x-4 gap-y-3">
            <span className="w-16 shrink-0 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              {t((d) => d.compare.metrics)}
            </span>
            <MetricPicker
              selected={state.metrics}
              onChange={(ids) => patch({ metrics: ids })}
              max={MAX_METRICS}
              familyFilter={familyFilter}
              onFamilyFilterChange={setFamilyFilter}
            />
            <div className="ml-auto flex flex-wrap items-center gap-x-4 gap-y-2">
              <Tabs
                value={state.mode}
                onValueChange={(v) => patch({ mode: v as CompareMode })}
              >
                <TabsList
                  aria-label={`${t((d) => d.compare.modeYear)} / ${t(
                    (d) => d.compare.modePeriod,
                  )}`}
                  className="h-8"
                >
                  <TabsTrigger value="year" className="h-7 px-3 text-xs">
                    {t((d) => d.compare.modeYear)}
                  </TabsTrigger>
                  <TabsTrigger value="period" className="h-7 px-3 text-xs">
                    {t((d) => d.compare.modePeriod)}
                  </TabsTrigger>
                </TabsList>
              </Tabs>
              <div className="flex items-center gap-2">
                <Switch
                  id="compare-witness"
                  checked={state.showWitness}
                  onCheckedChange={(v) => patch({ showWitness: v === true })}
                  aria-label={t((d) => d.compare.showWitness)}
                />
                <Label
                  htmlFor="compare-witness"
                  className="cursor-pointer text-xs"
                >
                  {t((d) => d.compare.showWitness)}
                </Label>
              </div>
            </div>
          </div>

          {/* Row 3 — global year slider (union) or period bounds */}
          {state.mode === "year" ? (
            <div className="flex items-center gap-x-4">
              <span className="w-16 shrink-0 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                {t((d) => d.common.year)}
              </span>
              {years.length > 0 ? (
                <YearSlider
                  years={years}
                  value={state.year}
                  onChange={(y) => patch({ year: y })}
                  className="min-w-0 flex-1"
                />
              ) : (
                <span className="text-xs text-muted-foreground">
                  {t((d) => d.common.loading)}
                </span>
              )}
            </div>
          ) : (
            <div className="flex flex-wrap items-center gap-x-4 gap-y-3">
              <span className="w-16 shrink-0 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                {t((d) => d.common.period)}
              </span>
              <div className="flex items-center gap-2">
                <Label
                  htmlFor="compare-from"
                  className="text-xs text-muted-foreground"
                >
                  {t((d) => d.common.from)}
                </Label>
                <Input
                  id="compare-from"
                  type="number"
                  inputMode="numeric"
                  min={minYear}
                  max={maxYear}
                  value={state.from}
                  onChange={(e) => {
                    const v = Number.parseInt(e.target.value, 10);
                    if (Number.isFinite(v))
                      patch({ from: Math.min(clampYear(v), state.to) });
                  }}
                  className="h-8 w-24 tnum"
                />
              </div>
              <div className="flex items-center gap-2">
                <Label
                  htmlFor="compare-to"
                  className="text-xs text-muted-foreground"
                >
                  {t((d) => d.common.to)}
                </Label>
                <Input
                  id="compare-to"
                  type="number"
                  inputMode="numeric"
                  min={minYear}
                  max={maxYear}
                  value={state.to}
                  onChange={(e) => {
                    const v = Number.parseInt(e.target.value, 10);
                    if (Number.isFinite(v))
                      patch({ to: Math.max(clampYear(v), state.from) });
                  }}
                  className="h-8 w-24 tnum"
                />
              </div>
              <span className="text-xs text-muted-foreground tnum">
                {minYear}–{maxYear}
              </span>
            </div>
          )}

          {/* Explains a widened range: with estimates on, one long-run
              estimation series can pull the slider far before any official
              data exists for the selection (e.g. 1816). */}
          {showWitnessRangeHint && (
            <p className="flex items-start gap-1.5 text-xs text-muted-foreground">
              <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
              <span>
                {interpolate(t((d) => d.compare.witnessRangeHint), {
                  year: witnessMin as number,
                })}
              </span>
            </p>
          )}
        </CardContent>
      </Card>

      <section
        className="mt-8 space-y-6"
        aria-label={t((d) => d.compare.title)}
      >
        {globalError ? (
          <ErrorBlock
            onRetry={() => {
              entities.refetch();
              catalog.refetch();
            }}
          />
        ) : state.countries.length === 0 ? (
          <EmptyBlock message={t((d) => d.compare.pickCountriesFirst)} />
        ) : state.metrics.length === 0 ? (
          <EmptyBlock message={t((d) => d.compare.pickMetricsFirst)} />
        ) : (
          <>
            {state.metrics.length >= 2 && state.countries.length >= 2 && (
              <SynthesisGrid
                metrics={state.metrics}
                countries={state.countries}
                from={state.mode === "year" ? state.year : state.from}
                to={state.mode === "year" ? state.year : state.to}
              />
            )}
            <div className="grid grid-cols-1 items-start gap-6 md:grid-cols-2">
              {state.metrics.map((id, i) => (
                <MetricCard
                  key={id}
                  index={i}
                  metricId={id}
                  countries={state.countries}
                  mode={state.mode}
                  year={state.year}
                  from={state.from}
                  to={state.to}
                  showWitness={state.showWitness}
                  sexChoice={state.sexChoices[id] ?? "all"}
                  onSexChange={(c) => setSex(id, c)}
                />
              ))}
            </div>
          </>
        )}
      </section>
    </div>
  );
}

/* --------------------------- Suspense-wrapped page --------------------------- */

export default function ComparePageView() {
  return (
    <Suspense
      fallback={
        <div className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6">
          <SkeletonRows rows={10} />
        </div>
      }
    >
      <CompareView />
    </Suspense>
  );
}
