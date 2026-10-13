"use client";

import * as React from "react";
import { RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { interpolate, useIndicatorLabel, useI18n } from "@/lib/toddlab/i18n";
import type { ScoreEntityComponent } from "@/lib/toddlab/client";

const MAX_WEIGHT = 20;

/**
 * Custom weights — the frontend's contract job (docs/score-contract.md):
 * applied client-side to the stored normalised values. Zero excludes a
 * component (and lowers coverage).
 */
export function ScoreWeightsPanel({
  components,
  weights,
  onChange,
  onReset,
  totalWeight,
}: {
  components: ScoreEntityComponent[];
  weights: Record<string, number>;
  onChange: (key: string, value: number) => void;
  onReset: () => void;
  totalWeight: number;
}) {
  const { t } = useI18n();
  const indicatorLabel = useIndicatorLabel();
  const [showAll, setShowAll] = React.useState(false);

  const ordered = React.useMemo(
    () =>
      [...components].sort(
        (a, b) => (weights[b.key] ?? 0) - (weights[a.key] ?? 0) || a.key.localeCompare(b.key),
      ),
    [components, weights],
  );
  const visible = showAll ? ordered : ordered.slice(0, 8);

  return (
    <div className="space-y-3">
      <p className="text-sm text-muted-foreground">{t((d) => d.score.weightsHint)}</p>
      <div className="flex items-center justify-between gap-3">
        <span className="tnum text-sm font-medium">
          {interpolate(t((d) => d.score.weightsTotal), {
            w: Number.isInteger(totalWeight) ? totalWeight : totalWeight.toFixed(1),
          })}
        </span>
        <Button variant="outline" size="sm" className="gap-1.5" onClick={onReset}>
          <RotateCcw className="h-3.5 w-3.5" />
          {t((d) => d.score.weightsReset)}
        </Button>
      </div>
      <ul className="space-y-2.5">
        {visible.map((c) => {
          const w = weights[c.key] ?? 0;
          const label =
            indicatorLabel(c.indicator, c.label_en) +
            (c.sex === "male"
              ? ` ${t((d) => d.score.sexMale)}`
              : c.sex === "female"
                ? ` ${t((d) => d.score.sexFemale)}`
                : "");
          return (
            <li key={c.key} className="grid grid-cols-[1fr_auto] items-center gap-x-3 gap-y-1 sm:grid-cols-[minmax(0,16rem)_1fr_auto]">
              <span className="min-w-0 truncate text-sm" title={label}>
                {label}
              </span>
              <Slider
                min={0}
                max={MAX_WEIGHT}
                step={1}
                value={[w]}
                onValueChange={([v]) => onChange(c.key, v)}
                className="w-full"
                aria-label={label}
              />
              <span className="tnum w-8 text-right text-sm font-medium">{w}</span>
            </li>
          );
        })}
      </ul>
      {ordered.length > 8 && (
        <button
          type="button"
          onClick={() => setShowAll((v) => !v)}
          className="text-sm text-primary underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
        >
          {showAll ? t((d) => d.common.showLess) : t((d) => d.common.showMore)}
        </button>
      )}
    </div>
  );
}
