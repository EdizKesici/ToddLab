"use client";

import { useMemo } from "react";
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
import { ChartTooltipShell } from "@/components/shared/charts";
import { ErrorBlock, LoadingBlock } from "@/components/shared/states";
import { useSeries } from "@/lib/toddlab/client";
import { fmtNumber } from "@/lib/toddlab/format";
import { useI18n, type Lang } from "@/lib/toddlab/i18n";

interface Row {
  year: number;
  canonical: number | null;
  witness: number | null;
}

const YEAR_MIN = 1960;
const YEAR_MAX = 2000;
const DEFAULT_UNIT = "deaths_per_1000_births";

interface TooltipItem {
  dataKey?: string | number;
  value?: number | string | Array<number | string>;
}

function FoundingTooltip({
  active,
  payload,
  label,
  canonicalLabel,
  witnessLabel,
  unit,
  lang,
}: {
  active?: boolean;
  payload?: TooltipItem[];
  label?: number | string;
  canonicalLabel: string;
  witnessLabel: string;
  unit: string;
  lang: Lang;
}) {
  if (!active || !payload || payload.length === 0) return null;

  const rows: {
    label: string;
    value: string;
    color: string;
    dashed?: boolean;
  }[] = [];

  for (const item of payload) {
    const v = typeof item.value === "number" ? item.value : null;
    if (v === null) continue;
    if (item.dataKey === "canonical") {
      rows.push({
        label: canonicalLabel,
        value: `${fmtNumber(v, unit, lang)} ‰`,
        color: "var(--chart-1)",
      });
    } else if (item.dataKey === "witness") {
      rows.push({
        label: witnessLabel,
        value: `${fmtNumber(v, unit, lang)} ‰`,
        color: "var(--witness)",
        dashed: true,
      });
    }
  }
  if (rows.length === 0) return null;

  return <ChartTooltipShell title={String(label)} rows={rows} />;
}

export function FoundingCaseChart() {
  const { t, lang } = useI18n();
  const query = useSeries("infant_mortality", ["ussr", "russian_federation"]);
  const data = query.data;

  const rows = useMemo<Row[]>(() => {
    if (!data) return [];
    const byYear = new Map<number, Row>();
    for (let y = YEAR_MIN; y <= YEAR_MAX; y++) {
      byYear.set(y, { year: y, canonical: null, witness: null });
    }
    for (const p of data.canonical) {
      if (p.entity_id !== "ussr" || p.value === null) continue;
      if (p.year < YEAR_MIN || p.year > YEAR_MAX) continue;
      const row = byYear.get(p.year);
      if (row) row.canonical = p.value;
    }
    const witness =
      data.witnesses.find((w) => w.key.includes("owid")) ?? data.witnesses[0];
    if (witness) {
      for (const p of witness.points) {
        if (p.entity_id !== "russian_federation" || p.value === null) continue;
        if (p.year < YEAR_MIN || p.year > YEAR_MAX) continue;
        const row = byYear.get(p.year);
        if (row) row.witness = p.value;
      }
    }
    return [...byYear.values()];
  }, [data]);

  if (query.isLoading) {
    return <LoadingBlock className="min-h-72" label={t((d) => d.common.loading)} />;
  }
  if (query.isError || rows.length === 0) {
    return <ErrorBlock onRetry={() => query.refetch()} />;
  }

  const unit = data?.unit ?? DEFAULT_UNIT;

  return (
    <figure className="rounded-xl border bg-card p-4 sm:p-6">
      <figcaption className="mb-4 text-sm font-medium text-foreground/80">
        {t((d) => d.method.s4ChartTitle)}
      </figcaption>

      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={rows} margin={{ top: 16, right: 12, bottom: 0, left: 0 }}>
            <CartesianGrid vertical={false} />
            <XAxis
              dataKey="year"
              type="number"
              domain={[YEAR_MIN, YEAR_MAX]}
              ticks={[1960, 1970, 1980, 1990, 2000]}
              tickLine={false}
              axisLine={false}
              tickMargin={8}
              tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
            />
            <YAxis
              width={44}
              domain={[0, 40]}
              ticks={[0, 10, 20, 30, 40]}
              tickLine={false}
              axisLine={false}
              tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
              label={{
                value: "‰",
                angle: -90,
                position: "insideLeft",
                offset: 14,
                style: {
                  fill: "var(--muted-foreground)",
                  fontSize: 12,
                  textAnchor: "middle",
                },
              }}
            />
            <ReferenceArea
              x1={1976}
              x2={1987}
              fill="var(--muted)"
              fillOpacity={0.7}
              stroke="none"
              label={{
                value: t((d) => d.method.s4Blackout),
                position: "insideTop",
                offset: 8,
                style: {
                  fill: "var(--muted-foreground)",
                  fontSize: 10,
                  textAnchor: "middle",
                },
              }}
            />
            <Tooltip
              cursor={{ stroke: "var(--border)", strokeWidth: 1 }}
              content={
                <FoundingTooltip
                  canonicalLabel={t((d) => d.method.s4ChartCanonical)}
                  witnessLabel={t((d) => d.method.s4ChartWitness)}
                  unit={unit}
                  lang={lang}
                />
              }
            />
            <Line
              name="canonical"
              type="monotone"
              dataKey="canonical"
              stroke="var(--chart-1)"
              strokeWidth={2}
              dot={{ r: 3, fill: "var(--chart-1)", strokeWidth: 0 }}
              activeDot={{ r: 4.5 }}
              connectNulls={false}
              isAnimationActive={false}
            />
            <Line
              name="witness"
              type="monotone"
              dataKey="witness"
              stroke="var(--witness)"
              strokeWidth={1.75}
              strokeDasharray="6 4"
              dot={false}
              activeDot={{ r: 3.5 }}
              connectNulls={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-x-6 gap-y-2 border-t border-border/60 pt-3 text-xs text-muted-foreground">
        <span className="inline-flex items-center gap-2">
          <span
            aria-hidden
            className="inline-block h-0.5 w-6 rounded-full"
            style={{ background: "var(--chart-1)" }}
          />
          {t((d) => d.method.s4ChartCanonical)}
        </span>
        <span className="inline-flex items-center gap-2">
          <span
            aria-hidden
            className="inline-block h-0 w-6 border-t-2 border-dashed"
            style={{ borderColor: "var(--witness)" }}
          />
          {t((d) => d.method.s4ChartWitness)}
        </span>
      </div>
    </figure>
  );
}
