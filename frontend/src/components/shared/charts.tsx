"use client";

/** Chart shared config: categorical country colors, witness styling, tooltip shell. */

export const SERIES_COLORS = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
  "var(--chart-6)",
  "var(--chart-7)",
  "var(--chart-8)",
];

export function colorForSeries(i: number): string {
  return SERIES_COLORS[i % SERIES_COLORS.length];
}

export const WITNESS_COLOR = "var(--witness)";

export function ChartTooltipShell({
  title,
  rows,
}: {
  title: React.ReactNode;
  rows: { label: React.ReactNode; value: React.ReactNode; color?: string; dashed?: boolean }[];
}) {
  return (
    <div className="rounded-lg border bg-popover text-popover-foreground shadow-md px-3 py-2 text-xs max-w-72">
      <div className="mb-1.5 font-semibold">{title}</div>
      <div className="space-y-1">
        {rows.map((r, i) => (
          <div key={i} className="flex items-center justify-between gap-4">
            <span className="inline-flex items-center gap-1.5 text-muted-foreground">
              <span
                aria-hidden
                className="inline-block w-4"
                style={
                  r.color
                    ? {
                        borderTop: r.dashed
                          ? `2px dashed ${r.color}`
                          : undefined,
                        background: r.dashed ? undefined : r.color,
                        height: r.dashed ? 0 : 8,
                        borderRadius: 2,
                      }
                    : undefined
                }
              />
              {r.label}
            </span>
            <span className="tnum font-medium">{r.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
