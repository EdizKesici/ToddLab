"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useMemo } from "react";
import { motion } from "framer-motion";
import { Scale, TrendingUp } from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/shared/page-header";
import { ErrorBlock, LoadingBlock } from "@/components/shared/states";
import { ChartTooltipShell } from "@/components/shared/charts";
import { colorForIndex, EntityPicker } from "@/components/shared/entity-picker";
import { YearSlider } from "@/components/shared/year-slider";
import { ScoreMovers } from "./score-movers";
import { DownloadCsv } from "@/components/shared/download-csv";
import {
  interpolate,
  useEntityLabel,
  useI18n,
} from "@/lib/toddlab/i18n";
import {
  useEntities,
  useScoreCompare,
  useScoreMeta,
  useScoreRankings,
  type ScoreCompareEntity,
  type ScoreComparePayload,
  type ScoreComparePoint,
} from "@/lib/toddlab/client";
import { fmtCoverage, fmtScore } from "@/lib/toddlab/format";
import { storedPreset, type ScoreName, type ScoreScope } from "@/lib/toddlab/score-types";
import { cn } from "@/lib/utils";

/* ----------------------------- URL-as-state ------------------------------ */

type ViewPreset = "equal" | "todd";

const SCORE_VALUES: ScoreName[] = ["official", "modelled"];

function parseState(sp: Pick<URLSearchParams, "get">) {
  const s = sp.get("s");
  const p = sp.get("p");
  const m = sp.get("m");
  const yRaw = sp.get("y");
  const cRaw = sp.get("c");
  const fRaw = sp.get("f");
  const tRaw = sp.get("t");
  const y = yRaw === null ? null : Number.parseInt(yRaw, 10);
  const f = fRaw === null ? null : Number.parseInt(fRaw, 10);
  const to = tRaw === null ? null : Number.parseInt(tRaw, 10);
  const compare =
    cRaw === null
      ? []
      : cRaw
          .split(",")
          .map((x) => x.trim())
          .filter((x) => /^[a-z][a-z0-9_]*$/.test(x))
          .slice(0, 4);
  return {
    score: SCORE_VALUES.includes(s as ScoreName) ? (s as ScoreName) : "official",
    preset: p === "todd" ? ("todd" as ViewPreset) : ("equal" as ViewPreset),
    scope: m === "todd" ? ("todd" as ScoreScope) : ("all" as ScoreScope),
    year: y !== null && Number.isFinite(y) ? y : null,
    compare,
    /** "both": official and modelled charts side by side (never merged). */
    view: sp.get("v") === "both" ? ("both" as const) : ("one" as const),
    moversFrom: f !== null && Number.isFinite(f) ? f : null,
    moversTo: to !== null && Number.isFinite(to) ? to : null,
  };
}

function Segmented<T extends string>({
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
    <div
      role="group"
      aria-label={ariaLabel}
      className="inline-flex rounded-lg bg-muted p-0.5"
    >
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          aria-pressed={value === o.value}
          onClick={() => onChange(o.value)}
          className={cn(
            "rounded-md px-3 py-1.5 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
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

function CoveragePill({ coverage, n, total }: { coverage: number; n: number; total: number | null }) {
  const tone =
    coverage >= 0.9
      ? "border-emerald-600/30 bg-emerald-600/10 text-emerald-700 dark:text-emerald-400"
      : coverage >= 0.7
        ? "border-amber-600/30 bg-amber-600/10 text-amber-700 dark:text-amber-400"
        : "border-orange-600/30 bg-orange-600/10 text-orange-700 dark:text-orange-400";
  return (
    <Badge variant="outline" className={cn("gap-1 font-normal tnum", tone)}>
      {fmtCoverage(coverage)}
      {total !== null && (
        <span className="text-muted-foreground">
          · {n}/{total}
        </span>
      )}
    </Badge>
  );
}

export function ScoreView() {
  const router = useRouter();
  const sp = useSearchParams();
  const { t, lang } = useI18n();
  const entityLabel = useEntityLabel();

  const state = useMemo(() => parseState(sp), [sp]);

  const patch = useCallback(
    (
      partial: Partial<{
        score: ScoreName;
        preset: ViewPreset;
        scope: ScoreScope;
        year: number | null;
        compare: string[];
        view: "one" | "both";
        moversFrom: number | null;
        moversTo: number | null;
      }>,
    ) => {
      const current = parseState(new URLSearchParams(window.location.search));
      const next = { ...current, ...partial };
      const q = new URLSearchParams();
      q.set("s", next.score);
      q.set("p", next.preset);
      if (next.scope === "todd") q.set("m", "todd");
      if (next.year !== null) q.set("y", String(next.year));
      if (next.compare.length > 0) q.set("c", next.compare.join(","));
      if (next.view === "both") q.set("v", "both");
      if (next.moversFrom !== null) q.set("f", String(next.moversFrom));
      if (next.moversTo !== null) q.set("t", String(next.moversTo));
      router.replace(`/score?${q.toString()}`, { scroll: false });
    },
    [router],
  );

  const rankings = useScoreRankings(state.year);
  const meta = useScoreMeta();
  const entities = useEntities();
  const stored = storedPreset(state.preset, state.scope);
  const both = state.view === "both";
  // Two independent queries: official and modelled are separate calculations and
  // are never merged; in the one-score view only the selected one is fetched.
  const officialCompare = useScoreCompare(
    both || state.score === "official" ? state.compare : [],
    "official",
    stored,
  );
  const modelledCompare = useScoreCompare(
    both || state.score === "modelled" ? state.compare : [],
    "modelled",
    stored,
  );
  const compareQuery = state.score === "official" ? officialCompare : modelledCompare;

  const labelOf = useCallback(
    (id: string) => entityLabel(id, entities.data?.entities.find((e) => e.entity_id === id)?.label),
    [entityLabel, entities.data],
  );

  const data = rankings.data;
  const years = data?.years[state.score] ?? [];
  const rows = data?.rankings[state.score][stored] ?? [];
  const totalComponents = meta.data
    ? Object.values(meta.data.presets[state.score][stored] ?? {}).filter((w) => w > 0).length
    : null;

  // When the selected year does not exist for the (possibly switched) score,
  // snap to that score's default year once the payload is known.
  React.useEffect(() => {
    if (!data) return;
    if (state.year !== null && !data.years[state.score].includes(state.year)) {
      patch({ year: data.default_year[state.score] });
    }
  }, [data, state.score, state.year, patch]);

  const [filter, setFilter] = React.useState("");
  const filtered = useMemo(() => {
    const f = filter.trim().toLowerCase();
    if (!f) return rows;
    return rows.filter((r) => labelOf(r.entity_id).toLowerCase().includes(f));
  }, [rows, filter, labelOf]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
      <PageHeader
        title={t((d) => d.score.title)}
        subtitle={t((d) => d.score.subtitle)}
        subtitleClassName="max-w-none text-pretty"
      />

      {rankings.isError ? (
        <ErrorBlock onRetry={() => rankings.refetch()} className="min-h-72" />
      ) : rankings.isLoading || !data ? (
        <LoadingBlock label={t((d) => d.common.loading)} className="min-h-72" />
      ) : (
        <>
          {/* Controls */}
          <div className="mb-6 flex flex-col gap-4 rounded-xl border bg-card p-4 sm:p-5">
            <div className="flex flex-wrap items-center gap-3">
              <Segmented<ScoreName>
                ariaLabel={t((d) => d.score.title)}
                value={state.score}
                onChange={(s) => patch({ score: s })}
                options={[
                  { value: "official", label: t((d) => d.score.official) },
                  { value: "modelled", label: t((d) => d.score.modelled) },
                ]}
              />
              <Segmented<ViewPreset>
                ariaLabel={t((d) => d.score.preset)}
                value={state.preset}
                onChange={(p) => patch({ preset: p })}
                options={[
                  { value: "equal", label: t((d) => d.score.presetEqual) },
                  { value: "todd", label: t((d) => d.score.presetTodd) },
                ]}
              />
              <Segmented<ScoreScope>
                ariaLabel={t((d) => d.score.scope)}
                value={state.scope}
                onChange={(m) => patch({ scope: m })}
                options={[
                  { value: "all", label: t((d) => d.score.scopeAll) },
                  { value: "todd", label: t((d) => d.score.scopeTodd) },
                ]}
              />
              <span className="text-sm text-muted-foreground">
                {interpolate(t((d) => d.score.rankedCountries), {
                  n: rows.length,
                })}
              </span>
            </div>
            <YearSlider
              years={years}
              value={data.year}
              onChange={(y) => patch({ year: y })}
              className="max-w-2xl"
            />
            <div className="grid gap-1.5 text-xs leading-relaxed text-muted-foreground sm:grid-cols-2">
              <p>
                {state.score === "official"
                  ? t((d) => d.score.officialHint)
                  : t((d) => d.score.modelledHint)}{" "}
                {t((d) => d.score.scopeHint)}
              </p>
              <p>
                {interpolate(t((d) => d.score.thresholdNote), {
                  t: meta.data
                    ? String(Math.round(meta.data.global.coverage_threshold * 100))
                    : "60",
                })}{" "}
                {data.year !== 0 &&
                  interpolate(t((d) => d.score.maxObsNote), {
                    year: data.max_obs_year[state.score],
                  })}
              </p>
            </div>
          </div>

          {/* Rankings table */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <CardTitle className="flex items-center gap-2 font-serif-display text-lg">
                  <Scale className="h-4 w-4 text-primary" />
                  {t((d) => d.score.title)} · {data.year}
                </CardTitle>
                <div className="flex flex-wrap items-center gap-2">
                  <DownloadCsv
                    href={`/api/score/export?score=${state.score}&preset=${stored}&year=${data.year}`}
                  />
                  <Input
                    value={filter}
                    onChange={(e) => setFilter(e.target.value)}
                    placeholder={t((d) => d.score.searchPlaceholder)}
                    className="h-9 w-full sm:w-64"
                    aria-label={t((d) => d.score.searchPlaceholder)}
                  />
                </div>
              </div>
            </CardHeader>
            <CardContent className="pt-0">
              {filtered.length === 0 ? (
                <p className="py-10 text-center text-sm text-muted-foreground">
                  {t((d) => d.common.noData)}
                </p>
              ) : (
                <div className="max-h-[520px] overflow-y-auto slim-scroll rounded-lg border">
                  <table className="w-full text-sm">
                    <thead className="sticky top-0 z-10 bg-muted/90 backdrop-blur-sm">
                      <tr className="text-left text-xs uppercase tracking-wide text-muted-foreground">
                        <th className="w-14 px-3 py-2 font-medium">#</th>
                        <th className="px-3 py-2 font-medium">{t((d) => d.score.tableCountry)}</th>
                        <th className="px-3 py-2 text-right font-medium">{t((d) => d.score.tableScore)}</th>
                        <th className="px-3 py-2 text-right font-medium">{t((d) => d.score.coverage)}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filtered.map((row, i) => (
                        <tr
                          key={row.entity_id}
                          className="border-t border-border/60 transition-colors hover:bg-accent/40"
                        >
                          <td className="px-3 py-2 tnum text-muted-foreground">{i + 1}</td>
                          <td className="px-3 py-2">
                            <Link
                              href={`/countries/${row.entity_id}`}
                              className="font-medium underline-offset-4 hover:text-primary hover:underline"
                            >
                              {labelOf(row.entity_id)}
                            </Link>
                          </td>
                          <td className="px-3 py-2 text-right tnum font-semibold">
                            {fmtScore(row.score, lang)}
                          </td>
                          <td className="px-3 py-2 text-right">
                            <CoveragePill
                              coverage={row.coverage}
                              n={row.n_components}
                              total={totalComponents}
                            />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Compare two countries over time */}
          <Card id="compare" className="mt-6 scroll-mt-20">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 font-serif-display text-lg">
                <TrendingUp className="h-4 w-4 text-primary" aria-hidden />
                {t((d) => d.score.compareTitle)}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 pt-0">
              <div className="flex flex-wrap items-center gap-3">
                <EntityPicker
                  selected={state.compare}
                  onChange={(ids) => patch({ compare: ids.slice(-4) })}
                  max={4}
                />
                <Segmented
                  ariaLabel={t((d) => d.score.compareView)}
                  value={state.view}
                  onChange={(v) => patch({ view: v })}
                  options={[
                    {
                      value: "one",
                      label: interpolate(t((d) => d.score.compareOneScore), {
                        score:
                          state.score === "official"
                            ? t((d) => d.score.official)
                            : t((d) => d.score.modelled),
                      }),
                    },
                    { value: "both", label: t((d) => d.score.compareSideBySide) },
                  ]}
                />
              </div>
              <p className="text-xs text-muted-foreground">{t((d) => d.score.compareHint)}</p>
              {state.compare.length === 0 ? (
                <p className="rounded-lg border border-dashed px-4 py-10 text-center text-sm text-muted-foreground">
                  {t((d) => d.score.compareEmpty)}
                </p>
              ) : both ? (
                <div className="grid gap-6 md:grid-cols-2">
                  {(
                    [
                      ["official", officialCompare],
                      ["modelled", modelledCompare],
                    ] as const
                  ).map(([name, q]) => (
                    <div key={name} className="min-w-0 space-y-2">
                      <h4 className="text-sm font-medium">
                        {name === "official" ? t((d) => d.score.official) : t((d) => d.score.modelled)}
                      </h4>
                      {q.isError ? (
                        <ErrorBlock onRetry={() => q.refetch()} className="min-h-48" />
                      ) : q.isLoading || !q.data ? (
                        <LoadingBlock label={t((d) => d.common.loading)} className="min-h-48" />
                      ) : (
                        <ScoreCompareChart data={q.data} selected={state.compare} labelOf={labelOf} />
                      )}
                    </div>
                  ))}
                </div>
              ) : compareQuery.isError ? (
                <ErrorBlock onRetry={() => compareQuery.refetch()} className="min-h-48" />
              ) : compareQuery.isLoading || !compareQuery.data ? (
                <LoadingBlock label={t((d) => d.common.loading)} className="min-h-48" />
              ) : (
                <ScoreCompareChart
                  data={compareQuery.data}
                  selected={state.compare}
                  labelOf={labelOf}
                />
              )}
            </CardContent>
          </Card>

          <ScoreMovers
            score={state.score}
            preset={stored}
            from={state.moversFrom}
            to={state.moversTo}
            onChange={(f, t2) => patch({ moversFrom: f, moversTo: t2 })}
          />

          {/* Notes */}
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-40px" }}
            transition={{ duration: 0.25, ease: "easeOut" }}
            className="mt-6 grid gap-3 text-sm leading-relaxed text-muted-foreground md:grid-cols-2"
          >
            <div className="rounded-xl border bg-card/60 p-4">
              {t((d) => d.score.twoScoresNote)}
            </div>
            <div className="rounded-xl border bg-card/60 p-4">
              {t((d) => d.score.carryRuleNote)}
            </div>
          </motion.div>
        </>
      )}
    </div>
  );
}

/* --------------------------- Score comparison ----------------------------- */

type CompareRow = { year: number } & Record<string, number | null>;

/** Contiguous runs of years flagged not comparable (consecutive years only). */
function notComparableSpans(data: ScoreComparePayload): { x1: number; x2: number }[] {
  const spans: { x1: number; x2: number }[] = [];
  let last: number | null = null;
  for (const y of data.comparability) {
    if (y.comparable) {
      last = null;
      continue;
    }
    if (last !== null && y.year === last + 1) spans[spans.length - 1].x2 = y.year + 0.5;
    else spans.push({ x1: y.year - 0.5, x2: y.year + 0.5 });
    last = y.year;
  }
  return spans;
}

function ScoreCompareChart({
  data,
  selected,
  labelOf,
}: {
  data: ScoreComparePayload;
  selected: string[];
  labelOf: (id: string) => string;
}) {
  const { t, lang } = useI18n();

  // Merge all series into one row per year, keeping the picker's order for
  // colors (chip i uses colorForIndex(i), so does line i).
  const rows = React.useMemo<CompareRow[]>(() => {
    const byYear = new Map<number, CompareRow>();
    for (const id of selected) {
      const ent = data.entities.find((e) => e.entity_id === id);
      if (!ent) continue;
      for (const p of ent.points) {
        let row = byYear.get(p.year);
        if (!row) {
          row = { year: p.year };
          byYear.set(p.year, row);
        }
        row[id] = p.score;
      }
    }
    return [...byYear.values()].sort((a, b) => a.year - b.year);
  }, [data, selected]);

  const series = React.useMemo(
    () =>
      selected
        .map((id) => ({ id, ent: data.entities.find((e) => e.entity_id === id) ?? null }))
        .filter((s): s is { id: string; ent: ScoreCompareEntity } => s.ent !== null),
    [data, selected],
  );

  const latest = React.useMemo(
    () =>
      series.map((s) => ({
        id: s.id,
        last: s.ent.points.length > 0 ? s.ent.points[s.ent.points.length - 1] : null,
      })),
    [series],
  );

  const spans = React.useMemo(() => notComparableSpans(data), [data]);
  const byYear = React.useMemo(
    () => new Map(data.comparability.map((c) => [c.year, c])),
    [data],
  );

  // The gap is read at the latest year where EVERY selected country is scored
  // (not at each country's own last year, which may differ), and flagged when
  // the countries share too little scored weight that year.
  const withPoints = series.filter((s) => s.ent.points.length > 0);
  const gapYear = React.useMemo(() => {
    if (withPoints.length < 2) return null;
    const common = data.comparability.filter((c) => c.n_entities === withPoints.length);
    return common.length > 0 ? common[common.length - 1] : null;
  }, [data, withPoints.length]);
  const gap = React.useMemo(() => {
    if (!gapYear) return null;
    const vals = withPoints
      .map((s) => s.ent.points.find((p) => p.year === gapYear.year)?.score)
      .filter((v): v is number => typeof v === "number");
    return vals.length >= 2 ? Math.max(...vals) - Math.min(...vals) : null;
  }, [gapYear, withPoints]);

  if (rows.length === 0) {
    return (
      <p className="rounded-lg border border-dashed px-4 py-10 text-center text-sm text-muted-foreground">
        {t((d) => d.score.noScoreEntity)}
      </p>
    );
  }

  const pct = String(Math.round(data.min_common_weight * 100));

  return (
    <div className="space-y-4">
      <div className="h-64 min-w-0">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={rows} margin={{ top: 6, right: 8, bottom: 0, left: -18 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
            {spans.map((sp) => (
              <ReferenceArea
                key={`${sp.x1}-${sp.x2}`}
                x1={sp.x1}
                x2={sp.x2}
                ifOverflow="hidden"
                fill="var(--muted-foreground)"
                fillOpacity={0.14}
                stroke="none"
              />
            ))}
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
                const tipRows: { label: string; value: string; color?: string }[] = payload
                  .filter((pl) => typeof pl.value === "number")
                  .map((pl, i) => {
                    const idx = selected.indexOf(String(pl.dataKey));
                    return {
                      label: labelOf(String(pl.dataKey)),
                      value: fmtScore(pl.value as number, lang),
                      color: colorForIndex(idx >= 0 ? idx : i),
                    };
                  });
                if (tipRows.length >= 2) {
                  const vals = payload
                    .map((pl) => pl.value)
                    .filter((v): v is number => typeof v === "number");
                  tipRows.push({
                    label: t((d) => d.score.compareGap),
                    value: fmtScore(Math.max(...vals) - Math.min(...vals), lang),
                  });
                  const cmp = byYear.get(Number(label));
                  if (cmp) {
                    tipRows.push({
                      label: t((d) => d.score.compareCommon),
                      value: `${Math.round(cmp.common_share * 100)} %${cmp.comparable ? "" : " · " + t((d) => d.score.compareNotComparable)}`,
                    });
                  }
                }
                return <ChartTooltipShell title={String(label)} rows={tipRows} />;
              }}
            />
            {series.map((s, i) => (
              <Line
                key={s.id}
                type="monotone"
                dataKey={s.id}
                name={labelOf(s.id)}
                stroke={colorForIndex(i)}
                strokeWidth={2}
                connectNulls={false}
                dot={{ r: 2, fill: colorForIndex(i), strokeWidth: 0 }}
                activeDot={{ r: 4 }}
                isAnimationActive={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      {spans.length > 0 && (
        <p className="flex items-start gap-2 text-xs text-muted-foreground">
          <span
            aria-hidden
            className="mt-0.5 inline-block h-3 w-5 shrink-0 rounded-sm bg-muted-foreground/20"
          />
          {interpolate(t((d) => d.score.compareLegendShade), { pct })}
        </p>
      )}

      {/* Latest scored year per country + gap */}
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
        {latest.map((l) => {
          const idx = series.findIndex((s) => s.id === l.id);
          return (
            <div key={l.id} className="inline-flex items-center gap-2">
              <span
                aria-hidden
                className="h-2 w-2 shrink-0 rounded-full"
                style={{ background: colorForIndex(idx >= 0 ? idx : 0) }}
              />
              <span className="font-medium">{labelOf(l.id)}</span>
              {l.last ? (
                <span className="tnum text-muted-foreground">
                  {fmtScore(l.last.score, lang)} ({l.last.year})
                </span>
              ) : (
                <span className="text-muted-foreground">{t((d) => d.score.noScoreEntity)}</span>
              )}
            </div>
          );
        })}
        {gap !== null && gapYear !== null ? (
          <div className="tnum inline-flex flex-wrap items-center gap-1.5 text-muted-foreground">
            <span>{interpolate(t((d) => d.score.compareGapAt), { year: String(gapYear.year) })} :</span>
            <span className="font-medium text-foreground">{fmtScore(gap, lang)}</span>
            <span>{t((d) => d.score.deltaPoints)}</span>
            <span>
              · {t((d) => d.score.compareCommon)} : {Math.round(gapYear.common_share * 100)} %
            </span>
            {!gapYear.comparable && (
              <Badge
                variant="outline"
                className="border-amber-600/30 bg-amber-600/10 font-normal text-amber-700 dark:text-amber-400"
              >
                {t((d) => d.score.compareNotComparable)}
              </Badge>
            )}
          </div>
        ) : (
          withPoints.length >= 2 && (
            <span className="text-muted-foreground">{t((d) => d.score.compareNoCommonYear)}</span>
          )
        )}
      </div>
    </div>
  );
}
