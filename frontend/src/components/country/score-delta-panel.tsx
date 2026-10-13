"use client";

import * as React from "react";
import { ScissorsLineDashed, TriangleAlert } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { interpolate, useI18n } from "@/lib/toddlab/i18n";
import { deltaBetweenYears, type ScoreCompSeries } from "@/lib/toddlab/score-core";
import { fmtCoverage, fmtPct1, fmtScore } from "@/lib/toddlab/format";
import { cn } from "@/lib/utils";

/**
 * Two-year difference per the v28 contract: only components available at BOTH
 * dates whose UNDERLYING OBSERVATION DIFFERS; refused when the common-weight
 * share is below delta_min_common_weight. Refusal is displayed as information.
 */
export function ScoreDeltaPanel({
  comps,
  years,
  minCommonWeight,
  labelOf,
}: {
  comps: ScoreCompSeries[];
  years: number[];
  minCommonWeight: number;
  labelOf: (key: string) => string;
}) {
  const { t, lang } = useI18n();

  const defaultFrom = years.length > 11 ? years[years.length - 11] : years[0];
  const [y1, setY1] = React.useState<number | null>(null);
  const [y2, setY2] = React.useState<number | null>(null);
  const from = y1 ?? defaultFrom;
  const to = y2 ?? years[years.length - 1];

  const result = React.useMemo(
    () =>
      Number.isFinite(from) && Number.isFinite(to) && from !== to
        ? deltaBetweenYears(comps, from, to, { minCommonWeight })
        : null,
    [comps, from, to, minCommonWeight],
  );

  const maxAbs = result
    ? Math.max(...result.decomposition.map((d) => Math.abs(d.term)), 0.0001)
    : 1;

  const yearSelect = (
    value: number,
    onChange: (y: number) => void,
    ariaLabel: string,
  ) => (
    <Select value={String(value)} onValueChange={(v) => onChange(Number(v))}>
      <SelectTrigger aria-label={ariaLabel} className="h-9 w-28">
        <SelectValue />
      </SelectTrigger>
      <SelectContent className="max-h-72">
        {years.map((y) => (
          <SelectItem key={y} value={String(y)} className="tnum">
            {y}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm text-muted-foreground">{t((d) => d.score.deltaFrom)}</span>
        {yearSelect(from, setY1, t((d) => d.score.deltaFrom))}
        <span className="text-sm text-muted-foreground">{t((d) => d.score.deltaTo)}</span>
        {yearSelect(to, setY2, t((d) => d.score.deltaTo))}
      </div>

      {!result ? (
        <p className="text-sm text-muted-foreground">
          {t((d) => d.score.deltaRefusedEmpty)}
        </p>
      ) : result.refused ? (
        <div
          role="note"
          className="flex items-start gap-2 rounded-lg border border-amber-500/40 bg-amber-500/5 px-4 py-3 text-sm text-amber-800 dark:text-amber-300"
        >
          <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0" />
          <span>
            {result.reason === "no_common_components"
              ? t((d) => d.score.deltaRefusedEmpty)
              : interpolate(t((d) => d.score.deltaRefusedWeight), {
                  p: fmtPct1(result.common_weight_share, lang),
                })}
          </span>
        </div>
      ) : (
        <>
          <div className="flex flex-wrap items-end gap-x-6 gap-y-2">
            <div>
              <div className="text-xs uppercase tracking-wide text-muted-foreground">
                {t((d) => d.score.deltaTitle)}
              </div>
              <div
                className={cn(
                  "tnum font-serif-display text-4xl font-semibold tracking-tight",
                  (result.delta ?? 0) >= 0 ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400",
                )}
              >
                {(result.delta ?? 0) >= 0 ? "+" : ""}
                {fmtScore(result.delta, lang)}
              </div>
            </div>
            <div className="space-y-0.5 pb-1 text-xs text-muted-foreground">
              <div>{interpolate(t((d) => d.score.deltaComponents), { n: result.n_components })}</div>
              <div>
                {interpolate(t((d) => d.score.deltaWeightShare), {
                  p: fmtPct1(result.common_weight_share, lang),
                })}
              </div>
            </div>
          </div>

          <div>
            <div className="mb-2 flex items-center gap-1.5 text-sm font-medium">
              <ScissorsLineDashed className="h-4 w-4 text-muted-foreground" />
              {t((d) => d.score.decomposition)}
            </div>
            <ul className="space-y-1.5">
              {result.decomposition.slice(0, 10).map((d) => (
                <li key={d.key} className="flex items-center gap-2 text-xs">
                  <span className="w-48 min-w-0 shrink-0 truncate sm:w-56" title={labelOf(d.key)}>
                    {labelOf(d.key)}
                  </span>
                  <div className="relative h-3 flex-1 rounded bg-muted/60" aria-hidden>
                    <div className="absolute inset-y-0 left-1/2 w-px bg-border" />
                    <div
                      className={cn(
                        "absolute inset-y-0 rounded",
                        d.term >= 0 ? "bg-emerald-500/70" : "bg-red-500/70",
                      )}
                      style={
                        d.term >= 0
                          ? { left: "50%", width: `${(Math.abs(d.term) / maxAbs) * 50}%` }
                          : { right: "50%", width: `${(Math.abs(d.term) / maxAbs) * 50}%` }
                      }
                    />
                  </div>
                  <span
                    className={cn(
                      "tnum w-16 shrink-0 text-right font-medium",
                      d.term >= 0 ? "text-emerald-700 dark:text-emerald-400" : "text-red-700 dark:text-red-400",
                    )}
                  >
                    {d.term >= 0 ? "+" : ""}
                    {d.term.toFixed(2)}
                  </span>
                  <Badge
                    variant="outline"
                    className="hidden h-4 shrink-0 px-1.5 text-[10px] font-normal text-muted-foreground tnum lg:inline-flex"
                    title={`${d.n1} (${d.obs1}) → ${d.n2} (${d.obs2})`}
                  >
                    {d.obs1 !== d.n1 ? d.obs1 : ""}→{d.obs2}
                  </Badge>
                </li>
              ))}
            </ul>
            {result.decomposition.length > 10 && (
              <p className="mt-1.5 text-xs text-muted-foreground">
                + {result.decomposition.length - 10} …
              </p>
            )}
            <p className="mt-2 text-xs text-muted-foreground">
              {t((d) => d.score.deltaExclusionNote)}
            </p>
          </div>
        </>
      )}
    </div>
  );
}
