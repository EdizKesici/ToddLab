"use client";

import { Slider } from "@/components/ui/slider";
import * as React from "react";

/** Discrete year slider over an available-years list. */
export function YearSlider({
  years,
  value,
  onChange,
  className,
}: {
  years: number[];
  value: number | null;
  onChange: (year: number) => void;
  className?: string;
}) {
  const idx = React.useMemo(() => {
    if (!value || years.length === 0) return years.length - 1;
    const found = years.indexOf(value);
    if (found >= 0) return found;
    // closest
    let best = 0;
    let bestDist = Infinity;
    years.forEach((y, i) => {
      const d = Math.abs(y - value);
      if (d < bestDist) {
        bestDist = d;
        best = i;
      }
    });
    return best;
  }, [years, value]);

  if (years.length === 0) return null;

  return (
    <div className={className}>
      <Slider
        min={0}
        max={years.length - 1}
        step={1}
        value={[idx]}
        onValueChange={([i]) => onChange(years[i])}
        aria-label="Year"
      />
      <div className="mt-1.5 flex justify-between text-xs text-muted-foreground tnum">
        <span>{years[0]}</span>
        <span className="font-semibold text-foreground text-sm">{years[idx]}</span>
        <span>{years[years.length - 1]}</span>
      </div>
    </div>
  );
}
