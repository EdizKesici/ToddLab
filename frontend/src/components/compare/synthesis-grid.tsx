"use client";

/**
 * Group synthesis — rank heatmap.
 * One row per selected country, one column per selected metric.
 * Rank (1 = best of the selection) respects higher_is_better:
 * - year mode   (from === to): value observed at that exact year.
 * - period mode (from < to)  : the country's LAST observed value within
 *   the period [from, to] — never an interpolation. The year actually
 *   used is disclosed in each cell's tooltip (sparse series end at
 *   different years; the period end itself may carry no data at all).
 * A metric column is shown only if at least one country has an observed
 * value in the window. Ranks use observed values only — a country with
 * a gap gets an empty cell, never a fabricated rank.
 */

import { Info } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { colorForIndex } from "@/components/shared/entity-picker";
import { EmptyBlock, SkeletonRows } from "@/components/shared/states";
import {
  useCatalog,
  useEntities,
  useSeries,
  type SeriesPoint,
} from "@/lib/toddlab/client";
import { fmtNumber } from "@/lib/toddlab/format";
import {
  useEntityLabel,
  useI18n,
  useIndicatorLabel,
  useUnitLabel,
} from "@/lib/toddlab/i18n";
import { cn } from "@/lib/utils";

/* ------------------------------ Shared rank kit ------------------------------ */

export interface RankInfo {
  rank: number;
  n: number;
}

/** Competition ranking ("1, 2, 2, 4") over non-null values only. */
export function computeRanks(
  entries: { id: string; value: number | null }[],
  higherIsBetter: boolean,
): Map<string, RankInfo> {
  const ranked = entries.filter(
    (e): e is { id: string; value: number } => e.value !== null,
  );
  const sorted = [...ranked].sort((a, b) =>
    higherIsBetter ? b.value - a.value : a.value - b.value,
  );
  const map = new Map<string, RankInfo>();
  let lastValue: number | null = null;
  let lastRank = 0;
  sorted.forEach((e, i) => {
    const rank = e.value === lastValue ? lastRank : i + 1;
    map.set(e.id, { rank, n: ranked.length });
    lastValue = e.value;
    lastRank = rank;
  });
  return map;
}

export type ValueBasis = "both" | "male" | "female" | null;

/**
 * Primary reported value among canonical points of one entity/year:
 * prefers the both-sexes row, then male, then female — always an observed
 * number, never an average or an interpolation (null when everything is a gap).
 */
export function pickPrimaryValue(
  points: SeriesPoint[],
): { value: number | null; basis: ValueBasis } {
  const both = points.find((p) => !p.sex && p.value !== null);
  if (both) return { value: both.value, basis: "both" };
  const male = points.find((p) => p.sex === "male" && p.value !== null);
  if (male) return { value: male.value, basis: "male" };
  const female = points.find((p) => p.sex === "female" && p.value !== null);
  if (female) return { value: female.value, basis: "female" };
  return { value: null, basis: null };
}

/** Colored rank badge: 1 = best (forest), last = worst (terracotta tint). */
export function RankBadge({
  rank,
  n,
  titleExtra,
  className,
}: {
  rank: number;
  n: number;
  titleExtra?: string;
  className?: string;
}) {
  const { t } = useI18n();
  const title = `${t((d) => d.common.rank)} ${rank} ${t((d) => d.common.of)} ${n}${
    titleExtra ? ` · ${titleExtra}` : ""
  }`;
  return (
    <Badge
      variant="outline"
      title={title}
      className={cn(
        "tnum justify-center min-w-8",
        rank === 1 && "bg-chart-8/15 text-chart-8 border-chart-8/30",
        rank === n && n > 1 && "bg-primary/10 text-primary border-primary/30",
        rank !== 1 && rank !== n && "text-muted-foreground",
        className,
      )}
    >
      {rank}
    </Badge>
  );
}

/* --------------------------------- Component --------------------------------- */

interface CellData {
  value: number | null;
  basis: ValueBasis;
  rank: number | null;
  n: number;
  unit: string;
  /** Year the value was actually observed at (within the window). */
  yearUsed: number | null;
}

interface ColumnReport {
  unit: string;
  cells: Map<string, CellData>;
}

export function SynthesisGrid({
  metrics,
  countries,
  from,
  to,
}: {
  metrics: string[];
  countries: string[];
  from: number;
  to: number;
}) {
  const { t, lang } = useI18n();
  const entityLabel = useEntityLabel();
  const { data: entitiesData } = useEntities();
  // undefined = query pending · null = settled, no observed value in the
  // window → hidden column
  const [reports, setReports] = useState<
    Record<string, ColumnReport | null | undefined>
  >({});

  const onReport = useCallback(
    (metricId: string, report: ColumnReport | null) => {
      setReports((prev) => {
        if (prev[metricId] === report) return prev;
        return { ...prev, [metricId]: report };
      });
    },
    [],
  );

  const visibleMetrics = metrics.filter((m) => reports[m]);
  // "Settled" = every metric either reported a column or was filtered out.
  const settled =
    metrics.length > 0 && metrics.every((m) => reports[m] !== undefined);

  /* Row order = average rank across the visible metric columns (lower is
     better). Countries with no rank at all keep their selection order at the
     end. This gives an instant "who is doing better overall" reading. */
  const orderedCountries = useMemo(() => {
    const avg = new Map<string, number | null>();
    for (const c of countries) {
      const ranks: number[] = [];
      for (const m of visibleMetrics) {
        const cell = reports[m]?.cells.get(c);
        if (cell?.rank != null) ranks.push(cell.rank);
      }
      avg.set(
        c,
        ranks.length > 0
          ? ranks.reduce((a, b) => a + b, 0) / ranks.length
          : null,
      );
    }
    return [...countries].sort((a, b) => {
      const ra = avg.get(a);
      const rb = avg.get(b);
      if (ra === null || ra === undefined) return rb === null || rb === undefined ? 0 : 1;
      if (rb === null || rb === undefined) return -1;
      if (ra !== rb) return ra - rb;
      return countries.indexOf(a) - countries.indexOf(b);
    });
  }, [countries, visibleMetrics, reports]);

  /** Heat tint for a cell: green toward rank 1, terracotta toward last. */
  const cellTint = (rank: number, n: number): string | undefined => {
    if (n <= 1) return undefined;
    const ratio = (rank - 1) / (n - 1); // 0 = best, 1 = worst
    const intensity = Math.abs(ratio - 0.5) * 2; // 0 middle → 1 extreme
    if (intensity < 0.05) return undefined;
    const hex = ratio < 0.5 ? "#0f766e" : "#b8431f";
    const alpha = (intensity * 0.16).toFixed(3);
    return `${hex}${Math.round(parseFloat(alpha) * 255)
      .toString(16)
      .padStart(2, "0")}`;
  };

  return (
    <>
      {/* Hook holders — render nothing, report rank cells via onReport. */}
      {metrics.map((m) => (
        <SynthesisColumn
          key={`${m}:${countries.join(",")}`}
          metricId={m}
          countries={countries}
          from={from}
          to={to}
          onReport={onReport}
        />
      ))}

      <Card className="gap-3 py-4">
        <CardHeader className="px-4 sm:px-6">
          <CardTitle className="flex items-center gap-2 text-base">
            {t((d) => d.compare.synthesis)}
            <TooltipProvider delayDuration={200}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    type="button"
                    aria-label={t((d) => d.compare.synthesisHint)}
                    className="rounded-full text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring"
                  >
                    <Info className="h-3.5 w-3.5" />
                  </button>
                </TooltipTrigger>
                <TooltipContent className="max-w-72 text-xs">
                  {t((d) => d.compare.synthesisHint)}
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </CardTitle>
        </CardHeader>
        <CardContent className="px-4 sm:px-6">
          {!settled ? (
            <SkeletonRows rows={Math.min(countries.length + 1, 6)} />
          ) : visibleMetrics.length === 0 || countries.length === 0 ? (
            <EmptyBlock
              message={t((d) => d.common.noData)}
              className="min-h-24"
            />
          ) : (
            <div className="max-h-96 overflow-y-auto slim-scroll">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs text-muted-foreground">
                      {t((d) => d.compare.tableCountry)}
                    </TableHead>
                    {visibleMetrics.map((m) => (
                      <SynthesisHeadCell key={m} metricId={m} />
                    ))}
                    <TableHead
                      className="min-w-16 text-right text-xs text-muted-foreground"
                      title={t((d) => d.common.lowerBetter)}
                    >
                      {t((d) => d.compare.synthesisAvg)}
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {orderedCountries.map((c) => {
                    const ci = countries.indexOf(c);
                    const ent = entitiesData?.entities.find(
                      (e) => e.entity_id === c,
                    );
                    // Average rank over the metrics where this country is ranked.
                    const ranks = visibleMetrics
                      .map((m) => reports[m]?.cells.get(c)?.rank)
                      .filter((r): r is number => r != null);
                    const avg =
                      ranks.length > 0
                        ? ranks.reduce((a, b) => a + b, 0) / ranks.length
                        : null;
                    return (
                      <TableRow key={c}>
                        <TableHead scope="row" className="max-w-40">
                          <span className="flex items-center gap-2 text-sm font-medium">
                            <span
                              aria-hidden
                              className="h-2 w-2 shrink-0 rounded-full"
                              style={{ background: colorForIndex(ci) }}
                            />
                            <span className="truncate">
                              {entityLabel(c, ent?.label)}
                            </span>
                          </span>
                        </TableHead>
                        {visibleMetrics.map((m) => {
                          const cell = reports[m]?.cells.get(c);
                          // Gap → empty cell, never a fabricated rank.
                          if (!cell || cell.rank === null)
                            return <TableCell key={m} />;
                          // Over a period, disclose the year the value is
                          // observed at (sparse series end at different years).
                          const titleParts = [
                            cell.basis === "male"
                              ? "M"
                              : cell.basis === "female"
                                ? "F"
                                : null,
                            from !== to && cell.yearUsed !== null
                              ? String(cell.yearUsed)
                              : null,
                          ].filter(Boolean);
                          return (
                            <TableCell
                              key={m}
                              className="py-1.5"
                              style={{ background: cellTint(cell.rank, cell.n) }}
                            >
                              <span className="flex items-center justify-between gap-2">
                                <span className="text-sm font-medium tnum">
                                  {cell.value !== null
                                    ? fmtNumber(cell.value, cell.unit, lang)
                                    : ""}
                                </span>
                                <RankBadge
                                  rank={cell.rank}
                                  n={cell.n}
                                  titleExtra={
                                    titleParts.length > 0
                                      ? titleParts.join(" · ")
                                      : undefined
                                  }
                                />
                              </span>
                            </TableCell>
                          );
                        })}
                        <TableCell className="text-right">
                          {avg !== null ? (
                            <span className="tnum text-sm font-semibold">
                              {avg.toFixed(1)}
                            </span>
                          ) : (
                            <span className="text-muted-foreground">-</span>
                          )}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </>
  );
}

function SynthesisHeadCell({ metricId }: { metricId: string }) {
  const indicatorLabel = useIndicatorLabel();
  const unitLabel = useUnitLabel();
  const { data: catalog } = useCatalog();
  const entry = catalog?.indicators.find((i) => i.id === metricId);
  const label = indicatorLabel(metricId, entry?.label ?? metricId);
  return (
    <TableHead className="min-w-24">
      <span
        className="block max-w-44 truncate text-xs font-medium"
        title={`${label}${entry ? ` · ${unitLabel(entry.unit)}` : ""}`}
      >
        {label}
      </span>
      {entry && (
        <span className="block text-[10px] font-normal text-muted-foreground">
          {unitLabel(entry.unit)}
        </span>
      )}
    </TableHead>
  );
}

/**
 * One metric column — owns its series query and reports rank cells up.
 * React Query dedupes with the identical queryKey used by the metric
 * cards, so this triggers no extra network request.
 *
 * Window semantics: year mode (from === to) keeps the exact-year match;
 * period mode takes the LAST year within [from, to] that carries an
 * observed value for the country — the window end itself often carries
 * none (series end at different years), which used to silently empty
 * the whole column.
 */
function SynthesisColumn({
  metricId,
  countries,
  from,
  to,
  onReport,
}: {
  metricId: string;
  countries: string[];
  from: number;
  to: number;
  onReport: (metricId: string, report: ColumnReport | null) => void;
}) {
  const { data, isPending, isError } = useSeries(metricId, countries);
  const countryKey = countries.join(",");

  useEffect(() => {
    if (isPending) return;
    if (isError || !data) {
      // Unavailable (503) or network error → no column at all.
      onReport(metricId, null);
      return;
    }
    const entries = countryKey
      .split(",")
      .filter(Boolean)
      .map((id) => {
        const inWindow = data.canonical.filter(
          (p) => p.entity_id === id && p.year >= from && p.year <= to,
        );
        // Latest year within the window that carries an observed value.
        let yearUsed: number | null = null;
        for (const p of inWindow) {
          if (p.value !== null && (yearUsed === null || p.year > yearUsed)) {
            yearUsed = p.year;
          }
        }
        if (yearUsed === null) {
          return { id, value: null, basis: null as ValueBasis, yearUsed: null };
        }
        const { value, basis } = pickPrimaryValue(
          inWindow.filter((p) => p.year === yearUsed),
        );
        return { id, value, basis, yearUsed };
      });
    const hasAny = entries.some((e) => e.value !== null);
    if (!hasAny) {
      onReport(metricId, null);
      return;
    }
    const ranks = computeRanks(entries, data.higher_is_better);
    const cells = new Map<string, CellData>();
    for (const e of entries) {
      const r = ranks.get(e.id);
      cells.set(e.id, {
        value: e.value,
        basis: e.basis,
        rank: r ? r.rank : null,
        n: r ? r.n : 0,
        unit: data.unit,
        yearUsed: e.yearUsed,
      });
    }
    onReport(metricId, { unit: data.unit, cells });
  }, [metricId, countryKey, from, to, isPending, isError, data, onReport]);

  return null;
}
