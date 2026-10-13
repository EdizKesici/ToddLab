"use client";

import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { ReliabilityBadge } from "@/components/shared/badges";
import { interpolate, useIndicatorLabel, useI18n } from "@/lib/toddlab/i18n";
import { useCatalog, type ScoreEntityComponent } from "@/lib/toddlab/client";
import { fmtScore } from "@/lib/toddlab/format";
import { cn } from "@/lib/utils";

/**
 * Component breakdown for one entity/score/year: normalised value (0-100),
 * weight in the active preset, source + badges. Carried values wear their
 * age ("data from YYYY") — never disguised as fresh measurements.
 */
export function ScoreComponentsList({
  components,
  weights,
  year,
  labelOf,
}: {
  components: ScoreEntityComponent[];
  weights: Record<string, number>;
  year: number;
  labelOf: (c: ScoreEntityComponent) => string;
}) {
  const { t, lang } = useI18n();
  const indicatorLabel = useIndicatorLabel();
  const catalog = useCatalog();
  const reliabilityOf = React.useCallback(
    (indicatorId: string) =>
      catalog.data?.indicators.find((e) => e.id === indicatorId)?.reliability,
    [catalog.data],
  );
  const [showAll, setShowAll] = React.useState(false);

  const rows = React.useMemo(() => {
    return [...components]
      .map((c) => ({
        c,
        weight: weights[c.key] ?? 0,
        value: c.normalised[String(year)],
        age: c.age[String(year)] ?? 0,
      }))
      .sort((a, b) => b.weight - a.weight || a.c.key.localeCompare(b.c.key));
  }, [components, weights, year]);

  const visible = showAll ? rows : rows.slice(0, 8);

  if (rows.length === 0) {
    return (
      <p className="py-6 text-center text-sm text-muted-foreground">
        {t((d) => d.common.noData)}
      </p>
    );
  }

  return (
    <div>
      <ul className="divide-y divide-border/60 rounded-lg border">
        {visible.map(({ c, weight, value, age }) => {
          const hasValue = value !== undefined;
          return (
            <li key={c.key} className="flex flex-col gap-1.5 px-3 py-2.5 sm:flex-row sm:items-center sm:gap-3">
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
                  <span className="text-sm font-medium">
                    {indicatorLabel(c.indicator, c.label_en)}
                    {c.sex === "male" && (
                      <span className="ml-1 text-xs text-muted-foreground">{t((d) => d.score.sexMale)}</span>
                    )}
                    {c.sex === "female" && (
                      <span className="ml-1 text-xs text-muted-foreground">{t((d) => d.score.sexFemale)}</span>
                    )}
                  </span>
                  <span className="tnum text-xs text-muted-foreground">
                    ×{Number.isInteger(weight) ? weight : weight.toFixed(1)}
                  </span>
                  {c.meta.transform === "log" && (
                    <Badge variant="outline" className="h-4 px-1.5 text-[10px] font-normal">
                      {t((d) => d.score.transformLog)}
                    </Badge>
                  )}
                  {c.meta.direction === "target" ? (
                    <Badge variant="outline" className="h-4 px-1.5 text-[10px] font-normal">
                      {t((d) => d.score.directionTarget)}
                    </Badge>
                  ) : (
                    <span className="text-[10px] text-muted-foreground">
                      {c.meta.direction === "higher"
                        ? t((d) => d.score.directionHigher)
                        : t((d) => d.score.directionLower)}
                    </span>
                  )}
                  {hasValue && age >= 1 && (
                    <Badge
                      variant="outline"
                      className="h-4 border-amber-600/40 bg-amber-600/10 px-1.5 text-[10px] font-normal text-amber-700 dark:text-amber-400"
                      title={interpolate(t((d) => d.score.carryRuleNote), {})}
                    >
                      {interpolate(t((d) => d.score.carryBadge), { year: year - age })}
                    </Badge>
                  )}
                  {c.meta.source_class === "modelled" && (
                    <Badge
                      variant="outline"
                      className="h-4 border-sky-600/40 bg-sky-600/10 px-1.5 text-[10px] font-normal text-sky-700 dark:text-sky-400"
                    >
                      {t((d) => d.score.modelledComponentBadge)}
                    </Badge>
                  )}
                  {(() => {
                    const rel = reliabilityOf(c.indicator);
                    return rel && rel !== "high" ? <ReliabilityBadge level={rel} className="h-4 px-1.5 text-[10px]" /> : null;
                  })()}
                </div>
              </div>
              <div className="flex shrink-0 items-center gap-2 sm:w-44">
                <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted" aria-hidden>
                  {hasValue && (
                    <div
                      className={cn("h-full rounded-full", age >= 1 ? "bg-amber-500/70" : "bg-primary/70")}
                      style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
                    />
                  )}
                </div>
                <span className={cn("tnum w-12 text-right text-sm", hasValue ? "font-medium" : "text-muted-foreground")}>
                  {hasValue ? fmtScore(value, lang) : "-"}
                </span>
              </div>
            </li>
          );
        })}
      </ul>
      {rows.length > 8 && (
        <button
          type="button"
          onClick={() => setShowAll((v) => !v)}
          className="mt-2 text-sm text-primary underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
        >
          {showAll ? t((d) => d.common.showLess) : t((d) => d.common.showMore)}
        </button>
      )}
    </div>
  );
}
