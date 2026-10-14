"use client";

/**
 * MetricCard — one card per selected metric on /compare.
 *
 * - year mode  : BarChart, one slot per country (exact year, no snapping),
 *                optional ghost witness bars (dashed gray), gaps stay empty.
 * - period mode: LineChart over [from..to], connectNulls={false} everywhere,
 *                optional dashed gray witness lines (both-sexes only).
 * - compact provenance table under the chart (values, witness, ranks or
 *   first/last observed + computed change).
 * Every tooltip keeps full provenance: provider + source_ref + citation
 * (canonical) or provider + root_label (witness). fmtNumber everywhere.
 */

import { motion } from "framer-motion";
import { Database } from "lucide-react";
import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
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
import { colorForIndex } from "@/components/shared/entity-picker";
import {
  DirectionBadge,
  ReliabilityBadge,
  ToddCoreBadge,
} from "@/components/shared/badges";
import { SexToggle, type SexChoice } from "@/components/shared/sex-toggle";
import { EmptyBlock, ErrorBlock, SkeletonRows } from "@/components/shared/states";
import {
  useEntities,
  useSeries,
  type SeriesPoint,
  type WitnessBlock,
} from "@/lib/toddlab/client";
import { fmtNumber, fmtTick } from "@/lib/toddlab/format";
import {
  useEntityLabel,
  useI18n,
  useIndicatorLabel,
  useUnitLabel,
  type Lang,
} from "@/lib/toddlab/i18n";
import {
  computeRanks,
  RankBadge,
  type ValueBasis,
} from "./synthesis-grid";
import type { CompareMode } from "./use-query-state";

/* ------------------------------ Local strings ------------------------------ */

/** Page-local strings (not in the shared dictionary on purpose). */
const LOCAL = {
  computed: { en: "change (computed)", fr: "variation (calculée)" },
} as const;

/* --------------------------------- Helpers --------------------------------- */

function trunc(s: string | null | undefined, n = 80): string {
  if (!s) return "";
  return s.length > n ? `${s.slice(0, n - 1)}…` : s;
}

function signedPercent(v: number, lang: Lang): string {
  const nf = new Intl.NumberFormat(lang === "fr" ? "fr-FR" : "en-US", {
    maximumFractionDigits: 1,
    signDisplay: "always",
  });
  return `${nf.format(v)} %`;
}

interface Provenance {
  provider?: string;
  sourceRef?: string;
  citation?: string;
  rootLabel?: string;
}

function provOf(p: SeriesPoint | undefined): Provenance {
  if (!p) return {};
  return { provider: p.provider, sourceRef: p.source_ref, citation: p.citation };
}

/** First witness value for a country at an exact year (blocks in order;
 *  prefers the both-sexes point; never invents). */
function witnessAtYear(
  witnesses: WitnessBlock[],
  entityId: string,
  year: number,
): { value: number; block: WitnessBlock } | null {
  for (const w of witnesses) {
    const pts = w.points.filter(
      (p) => p.entity_id === entityId && p.year === year,
    );
    const p =
      pts.find((pp) => !pp.sex && pp.value !== null) ??
      pts.find((pp) => pp.value !== null);
    if (p && p.value !== null) return { value: p.value, block: w };
  }
  return null;
}

/* ---------------------------------- Rows ---------------------------------- */

interface YearRow {
  id: string;
  label: string;
  color: string;
  /** single-bar canonical value (non-split metric, chosen sex, or reported both) */
  value: number | null;
  /** two-bar mode (sex_split + all, no reported both-sexes value) */
  valueM: number | null;
  valueF: number | null;
  basis: ValueBasis;
  witness: number | null;
  prov: Provenance;
  provM: Provenance;
  provF: Provenance;
  wprov: Provenance;
}

interface PeriodDef {
  key: string;
  entityId: string;
  sex?: "male" | "female";
  witness?: boolean;
}

type PeriodRow = Record<string, number | string | null>;

/* -------------------------------- Component -------------------------------- */

export function MetricCard({
  metricId,
  countries,
  mode,
  year,
  from,
  to,
  showWitness,
  sexChoice,
  onSexChange,
  index,
}: {
  metricId: string;
  countries: string[];
  mode: CompareMode;
  year: number;
  from: number;
  to: number;
  showWitness: boolean;
  sexChoice: SexChoice;
  onSexChange: (c: SexChoice) => void;
  index: number;
}) {
  const { lang, t } = useI18n();
  const indicatorLabel = useIndicatorLabel();
  const unitLabel = useUnitLabel();
  const entityLabel = useEntityLabel();
  const { data: entitiesData } = useEntities();

  const q = useSeries(metricId, countries);
  const data = q.data;

  const countriesKey = countries.join(",");
  const labels = useMemo(() => {
    const map = new Map<string, string>();
    for (const id of countries) {
      const ent = entitiesData?.entities.find((e) => e.entity_id === id);
      map.set(id, entityLabel(id, ent?.label));
    }
    return map;
  }, [countriesKey, entitiesData, entityLabel]);

  const unit = data?.unit ?? "";
  const unitLabelStr = data ? unitLabel(unit) : "";

  /* ------------------------------ Year mode data ------------------------------ */

  const yearRows = useMemo<YearRow[]>(() => {
    if (!data || mode !== "year") return [];
    const split = data.sex_split;
    const effSex: SexChoice = split ? sexChoice : "all";
    return countries.map((id, i) => {
      const pts = data.canonical.filter(
        (p) => p.entity_id === id && p.year === year,
      );
      const both = pts.find((p) => !p.sex);
      const male = pts.find((p) => p.sex === "male");
      const female = pts.find((p) => p.sex === "female");

      let value: number | null = null;
      let valueM: number | null = null;
      let valueF: number | null = null;
      let basis: ValueBasis = null;
      let prov: Provenance = {};
      let provM: Provenance = {};
      let provF: Provenance = {};

      if (!split) {
        value = both?.value ?? null;
        prov = provOf(both);
        if (value !== null) basis = "both";
      } else if (effSex === "male") {
        value = male?.value ?? null;
        prov = provOf(male);
        if (value !== null) basis = "male";
      } else if (effSex === "female") {
        value = female?.value ?? null;
        prov = provOf(female);
        if (value !== null) basis = "female";
      } else if (both && both.value !== null) {
        value = both.value;
        prov = provOf(both);
        basis = "both";
      } else {
        valueM = male?.value ?? null;
        valueF = female?.value ?? null;
        provM = provOf(male);
        provF = provOf(female);
        if (valueM !== null) basis = "male";
        else if (valueF !== null) basis = "female";
      }

      const wit = showWitness ? witnessAtYear(data.witnesses, id, year) : null;

      return {
        id,
        label: labels.get(id) ?? id,
        color: colorForIndex(i),
        value,
        valueM,
        valueF,
        basis,
        witness: wit ? wit.value : null,
        prov,
        provM,
        provF,
        wprov: wit
          ? {
              provider: wit.block.provider,
              sourceRef: wit.block.source_ref,
              rootLabel: wit.block.root_label,
            }
          : {},
      };
    });
  }, [data, mode, sexChoice, countriesKey, year, showWitness, labels]);

  const canonicalAnyYear = yearRows.some(
    (r) => r.value !== null || r.valueM !== null || r.valueF !== null,
  );
  const witnessAnyYear = yearRows.some((r) => r.witness !== null);
  const twoBarsYear = yearRows.some(
    (r) => r.value === null && (r.valueM !== null || r.valueF !== null),
  );

  const yearRanks = useMemo(() => {
    if (!data) return null;
    return computeRanks(
      yearRows.map((r) => ({
        id: r.id,
        value: r.value ?? r.valueM ?? r.valueF,
      })),
      data.higher_is_better,
    );
  }, [data, yearRows]);

  /* ----------------------------- Period mode data ----------------------------- */

  const period = useMemo<{
    defs: PeriodDef[];
    witnessDefs: PeriodDef[];
    rows: PeriodRow[];
    splitAll: boolean;
  } | null>(() => {
    if (!data || mode !== "period") return null;
    const split = data.sex_split;
    const effSex: SexChoice = split ? sexChoice : "all";
    const defs: PeriodDef[] = [];
    countries.forEach((id) => {
      if (split && effSex === "male") {
        defs.push({ key: `${id}:m`, entityId: id, sex: "male" });
      } else if (split && effSex === "female") {
        defs.push({ key: `${id}:f`, entityId: id, sex: "female" });
      } else if (split && effSex === "all") {
        // Some sex-split metrics carry only both-sexes canonical rows —
        // fall back to a single both-sexes line when no M/F rows exist.
        const hasSexRows = data.canonical.some(
          (p) =>
            p.entity_id === id && p.year >= from && p.year <= to && !!p.sex,
        );
        if (hasSexRows) {
          defs.push({ key: `${id}:m`, entityId: id, sex: "male" });
          defs.push({ key: `${id}:f`, entityId: id, sex: "female" });
        } else {
          defs.push({ key: id, entityId: id });
        }
      } else {
        defs.push({ key: id, entityId: id });
      }
    });

    // Witness lines: both-sexes points only (no sex), merged per country,
    // first block wins per year, gaps kept as nulls.
    const witnessDefs: PeriodDef[] = [];
    const witnessMaps = new Map<
      string,
      Map<number, { value: number; block: WitnessBlock }>
    >();
    if (showWitness) {
      for (const id of countries) {
        const map = new Map<number, { value: number; block: WitnessBlock }>();
        for (const w of data.witnesses) {
          for (const p of w.points) {
            if (p.entity_id !== id || p.sex || p.value === null) continue;
            if (p.year < from || p.year > to) continue;
            if (!map.has(p.year)) map.set(p.year, { value: p.value, block: w });
          }
        }
        if (map.size > 0) {
          witnessMaps.set(id, map);
          witnessDefs.push({ key: `${id}__w`, entityId: id, witness: true });
        }
      }
    }

    const rows: PeriodRow[] = [];
    for (let y = from; y <= to; y++) {
      const row: PeriodRow = { year: y };
      for (const d of defs) {
        const p = data.canonical.find(
          (c) =>
            c.entity_id === d.entityId &&
            c.year === y &&
            c.sex === d.sex,
        );
        row[d.key] = p ? p.value : null;
        row[`p_${d.key}`] = p?.provider ?? null;
        row[`r_${d.key}`] = p?.source_ref ?? null;
        row[`c_${d.key}`] = p?.citation ?? null;
      }
      for (const wd of witnessDefs) {
        const hit = witnessMaps.get(wd.entityId)?.get(y);
        row[wd.key] = hit ? hit.value : null;
        row[`p_${wd.key}`] = hit?.block.provider ?? null;
        row[`rl_${wd.key}`] = hit?.block.root_label ?? null;
      }
      rows.push(row);
    }
    return { defs, witnessDefs, rows, splitAll: defs.some((d) => !!d.sex) };
  }, [data, mode, sexChoice, countriesKey, from, to, showWitness]);

  const canonicalAnyPeriod = period
    ? period.rows.some((row) =>
        period.defs.some((d) => typeof row[d.key] === "number"),
      )
    : false;

  /* ------------------------------- Period table ------------------------------- */

  const periodTableRows = useMemo(() => {
    if (!period || !data || mode !== "period") return [];
    const split = data.sex_split;
    const effSex: SexChoice = split ? sexChoice : "all";
    return countries.map((id) => {
      // Single basis series per country: chosen sex when specific; otherwise
      // the first observed basis available in range (both → male → female).
      let basis: "both" | "male" | "female" = "both";
      if (split && (effSex === "male" || effSex === "female")) {
        basis = effSex;
      } else if (split) {
        const inRange = data.canonical.filter(
          (p) => p.entity_id === id && p.year >= from && p.year <= to,
        );
        if (!inRange.some((p) => !p.sex && p.value !== null)) {
          if (inRange.some((p) => p.sex === "male" && p.value !== null)) {
            basis = "male";
          } else if (
            inRange.some((p) => p.sex === "female" && p.value !== null)
          ) {
            basis = "female";
          }
        }
      }
      const matches = (p: SeriesPoint) =>
        basis === "both" ? !p.sex : p.sex === basis;
      const observed = data.canonical
        .filter(
          (p) =>
            p.entity_id === id &&
            p.year >= from &&
            p.year <= to &&
            p.value !== null &&
            matches(p),
        )
        .sort((a, b) => a.year - b.year);
      const first = observed[0] ?? null;
      const last = observed[observed.length - 1] ?? null;
      const variation =
        first && last && first.value !== null && last.value !== null && first.value !== 0
          ? ((last.value - first.value) / Math.abs(first.value)) * 100
          : null;
      return { id, basis, first, last, variation };
    });
  }, [period, data, mode, sexChoice, countriesKey, from, to]);

  /* --------------------------------- Render --------------------------------- */

  const unavailable =
    q.isError && (q.error as Error & { status?: number }).status === 503;

  let body: React.ReactNode;

  if (q.isPending && !data) {
    body = <SkeletonRows rows={6} />;
  } else if (q.isError) {
    body = unavailable ? (
      <div
        className="flex min-h-40 flex-col items-center justify-center gap-2 py-6 text-center text-sm text-muted-foreground"
        role="status"
      >
        <Database className="h-6 w-6" />
        <span className="font-medium text-foreground">
          {t((d) => d.indicators.unavailableTitle)}
        </span>
        <span className="max-w-md text-xs">
          {t((d) => d.indicators.unavailableText)}
        </span>
      </div>
    ) : (
      <ErrorBlock onRetry={() => q.refetch()} />
    );
  } else if (data && mode === "year") {
    const showChart = canonicalAnyYear || (showWitness && witnessAnyYear);
    body = showChart ? (
      <>
        {!canonicalAnyYear && showWitness && witnessAnyYear && (
          <div className="mb-2 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <Badge variant="secondary" className="gap-1">
              {t((d) => d.common.modelled)}
            </Badge>
            <span>{t((d) => d.common.witnessNote)}</span>
          </div>
        )}
        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={yearRows}
              barGap="-100%"
              margin={{ top: 8, right: 8, bottom: 0, left: 0 }}
            >
              <CartesianGrid vertical={false} />
              <XAxis
                dataKey="label"
                interval={0}
                height={58}
                angle={-25}
                textAnchor="end"
                tick={{ fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v: string) => (v.length > 14 ? `${v.slice(0, 13)}…` : v)}
              />
              <YAxis
                width={52}
                tick={{ fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v: number) => fmtTick(v, unit, lang)}
              />
              <Tooltip
                cursor={{ fill: "var(--muted)", fillOpacity: 0.45 }}
                content={(p) => (
                  <YearTooltip
                    active={p.active}
                    payload={p.payload as unknown as TooltipEntry[]}
                    unit={unit}
                    unitLabelStr={unitLabelStr}
                    lang={lang}
                  />
                )}
              />
              {showWitness && witnessAnyYear && (
                <Bar
                  dataKey="witness"
                  name={t((d) => d.compare.tableWitness)}
                  radius={[3, 3, 0, 0]}
                  maxBarSize={64}
                >
                  {yearRows.map((r) => (
                    <Cell
                      key={r.id}
                      fill={r.color}
                      fillOpacity={0.16}
                      stroke={r.color}
                      strokeDasharray="3 3"
                    />
                  ))}
                </Bar>
              )}
              {twoBarsYear ? (
                <>
                  <Bar
                    dataKey="valueM"
                    name={t((d) => d.common.male)}
                    maxBarSize={56}
                    radius={[3, 3, 0, 0]}
                  >
                    {yearRows.map((r, i) => (
                      <Cell key={r.id} fill={colorForIndex(i)} />
                    ))}
                  </Bar>
                  <Bar
                    dataKey="valueF"
                    name={t((d) => d.common.female)}
                    fillOpacity={0.55}
                    maxBarSize={56}
                    radius={[3, 3, 0, 0]}
                  >
                    {yearRows.map((r, i) => (
                      <Cell key={r.id} fill={colorForIndex(i)} />
                    ))}
                  </Bar>
                </>
              ) : (
                <Bar dataKey="value" maxBarSize={64} radius={[3, 3, 0, 0]}>
                  {yearRows.map((r, i) => (
                    <Cell key={r.id} fill={colorForIndex(i)} />
                  ))}
                </Bar>
              )}
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-muted-foreground">
          {twoBarsYear && (
            <>
              <LegendSwatch label={t((d) => d.common.male)} kind="solid" color="var(--foreground)" />
              <LegendSwatch
                label={t((d) => d.common.female)}
                kind="solid"
                color="var(--foreground)"
                faded
              />
            </>
          )}
          {showWitness && witnessAnyYear && (
            <LegendSwatch
              label={t((d) => d.compare.tableWitness)}
              kind="ghost"
              color="var(--foreground)"
            />
          )}
        </div>
        <p className="mt-1 text-[11px] text-muted-foreground/80">
          {t((d) => d.common.gapNote)}
        </p>
      </>
    ) : (
      <EmptyBlock
        className="min-h-40"
        message={t((d) => d.compare.metricCardEmpty)}
      />
    );
  } else if (data && mode === "period" && period) {
    const showChart = canonicalAnyPeriod || period.witnessDefs.length > 0;
    body = showChart ? (
      <>
        {!canonicalAnyPeriod && period.witnessDefs.length > 0 && (
          <div className="mb-2 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <Badge variant="secondary" className="gap-1">
              {t((d) => d.common.modelled)}
            </Badge>
            <span>{t((d) => d.common.witnessNote)}</span>
          </div>
        )}
        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={period.rows}
              margin={{ top: 8, right: 8, bottom: 0, left: 0 }}
            >
              <CartesianGrid vertical={false} />
              <XAxis
                dataKey="year"
                tick={{ fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                minTickGap={28}
                interval="preserveStartEnd"
              />
              <YAxis
                width={52}
                domain={["auto", "auto"]}
                tick={{ fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v: number) => fmtTick(v, unit, lang)}
              />
              <Tooltip
                cursor={{ stroke: "var(--border)" }}
                content={(p) => (
                  <PeriodTooltip
                    active={p.active}
                    payload={p.payload as unknown as TooltipEntry[]}
                    defs={period.defs}
                    labels={labels}
                    countries={countries}
                    unit={unit}
                    unitLabelStr={unitLabelStr}
                    lang={lang}
                  />
                )}
              />
              {period.defs.map((d) => {
                const color = colorForIndex(countries.indexOf(d.entityId));
                const isF = d.sex === "female";
                return (
                  <Line
                    key={d.key}
                    type="linear"
                    dataKey={d.key}
                    stroke={color}
                    strokeWidth={1.75}
                    strokeDasharray={isF ? "5 3" : undefined}
                    strokeOpacity={isF ? 0.85 : 1}
                    dot={{ r: 1.6, strokeWidth: 0, fill: color, fillOpacity: isF ? 0.85 : 1 }}
                    activeDot={{ r: 3.5 }}
                    connectNulls={false}
                    isAnimationActive={false}
                  />
                );
              })}
              {period.witnessDefs.map((d) => {
                const wColor = colorForIndex(countries.indexOf(d.entityId));
                return (
                  <Line
                    key={d.key}
                    type="linear"
                    dataKey={d.key}
                    stroke={wColor}
                    strokeWidth={1.5}
                    strokeDasharray="2 4"
                    strokeOpacity={0.9}
                    dot={false}
                    activeDot={{ r: 3, stroke: wColor }}
                    connectNulls={false}
                    isAnimationActive={false}
                  />
                );
              })}
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-muted-foreground">
          {countries.map((id, i) => (
            <LegendSwatch
              key={id}
              label={labels.get(id) ?? id}
              kind="dot"
              color={colorForIndex(i)}
            />
          ))}
          {period.splitAll && (
            <>
              <LegendSwatch label="M" kind="solid" color="var(--foreground)" />
              <LegendSwatch
                label="F"
                kind="dashed"
                color="var(--foreground)"
              />
            </>
          )}
          {period.witnessDefs.length > 0 && (
            <LegendSwatch
              label={t((d) => d.compare.tableWitness)}
              kind="dotted"
              color="var(--foreground)"
            />
          )}
        </div>
        <p className="mt-1 text-[11px] text-muted-foreground/80">
          {t((d) => d.common.gapNote)}
        </p>
      </>
    ) : (
      <EmptyBlock
        className="min-h-40"
        message={t((d) => d.compare.metricCardEmpty)}
      />
    );
  } else {
    body = <SkeletonRows rows={6} />;
  }

  /* --------------------------------- Tables --------------------------------- */

  const table = data ? (
    mode === "year" ? (
      <Table className="mt-3 text-xs">
        <TableHeader>
          <TableRow>
            <TableHead className="h-8 text-xs">
              {t((d) => d.compare.tableCountry)}
            </TableHead>
            <TableHead className="h-8 text-xs text-right">
              {t((d) => d.compare.tableValue)} ({year})
            </TableHead>
            <TableHead className="h-8 text-xs text-right">
              {t((d) => d.compare.tableWitness)}
            </TableHead>
            <TableHead className="h-8 text-xs text-right">
              {t((d) => d.compare.rankInSelection)}
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {yearRows.map((r) => {
            const rank = yearRanks?.get(r.id);
            return (
              <TableRow key={r.id}>
                <TableCell className="py-1.5">
                  <span className="flex items-center gap-2 font-medium">
                    <span
                      aria-hidden
                      className="h-2 w-2 shrink-0 rounded-full"
                      style={{ background: r.color }}
                    />
                    <span className="max-w-36 truncate">{r.label}</span>
                  </span>
                </TableCell>
                <TableCell className="py-1.5 text-right tnum">
                  {r.value !== null ? (
                    <span title={provTitle(r.prov)}>
                      {fmtNumber(r.value, unit, lang)}
                    </span>
                  ) : r.valueM !== null || r.valueF !== null ? (
                    <span className="inline-flex flex-col items-end leading-tight">
                      {r.valueM !== null && (
                        <span title={provTitle(r.provM)}>
                          <span className="mr-1 text-[10px] text-muted-foreground">M</span>
                          {fmtNumber(r.valueM, unit, lang)}
                        </span>
                      )}
                      {r.valueF !== null && (
                        <span title={provTitle(r.provF)}>
                          <span className="mr-1 text-[10px] text-muted-foreground">F</span>
                          {fmtNumber(r.valueF, unit, lang)}
                        </span>
                      )}
                    </span>
                  ) : (
                    // Gap → empty cell (never interpolated)
                    <span className="sr-only">{t((d) => d.compare.noDataShort)}</span>
                  )}
                </TableCell>
                <TableCell
                  className="py-1.5 text-right tnum text-muted-foreground"
                  title={r.witness !== null ? r.wprov.rootLabel : undefined}
                >
                  {r.witness !== null ? fmtNumber(r.witness, unit, lang) : ""}
                </TableCell>
                <TableCell className="py-1.5 text-right">
                  {rank ? (
                    <RankBadge
                      rank={rank.rank}
                      n={rank.n}
                      titleExtra={
                        r.basis === "male"
                          ? "M"
                          : r.basis === "female"
                            ? "F"
                            : undefined
                      }
                      className="ml-auto"
                    />
                  ) : (
                    ""
                  )}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    ) : (
      <Table className="mt-3 text-xs">
        <TableHeader>
          <TableRow>
            <TableHead className="h-8 text-xs">
              {t((d) => d.compare.tableCountry)}
            </TableHead>
            <TableHead className="h-8 text-xs text-right">{from} →</TableHead>
            <TableHead className="h-8 text-xs text-right">→ {to}</TableHead>
            <TableHead
              className="h-8 text-right text-xs"
              title={LOCAL.computed[lang]}
            >
              {LOCAL.computed[lang]} *
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {periodTableRows.map((r) => (
            <TableRow key={r.id}>
              <TableCell className="py-1.5">
                <span className="flex items-center gap-2 font-medium">
                  <span
                    aria-hidden
                    className="h-2 w-2 shrink-0 rounded-full"
                    style={{
                      background: colorForIndex(countries.indexOf(r.id)),
                    }}
                  />
                  <span className="max-w-36 truncate">
                    {labels.get(r.id) ?? r.id}
                    {r.basis !== "both" && (
                      <span className="ml-1 text-[10px] font-normal text-muted-foreground">
                        {r.basis === "male" ? "M" : "F"}
                      </span>
                    )}
                  </span>
                </span>
              </TableCell>
              <TableCell className="py-1.5 text-right tnum">
                {r.first ? (
                  <span title={provTitle(provOf(r.first))}>
                    {fmtNumber(r.first.value, unit, lang)}{" "}
                    <span className="text-muted-foreground">
                      ({r.first.year})
                    </span>
                  </span>
                ) : (
                  ""
                )}
              </TableCell>
              <TableCell className="py-1.5 text-right tnum">
                {r.last ? (
                  <span title={provTitle(provOf(r.last))}>
                    {fmtNumber(r.last.value, unit, lang)}{" "}
                    <span className="text-muted-foreground">
                      ({r.last.year})
                    </span>
                  </span>
                ) : (
                  ""
                )}
              </TableCell>
              <TableCell
                className="py-1.5 text-right tnum"
                title={LOCAL.computed[lang]}
              >
                {r.variation !== null ? signedPercent(r.variation, lang) : ""}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    )
  ) : null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.22, delay: Math.min(index * 0.06, 0.3), ease: "easeOut" }}
      className="h-full"
    >
      <Card className="h-full gap-3 py-4">
        <CardHeader className="px-4 sm:px-6">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div className="min-w-0">
              <CardTitle className="text-base leading-snug">
                {indicatorLabel(metricId, data?.label ?? metricId)}
              </CardTitle>
              <div className="mt-1.5 flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
                {data?.todd_core && <ToddCoreBadge compact />}
                {data && <ReliabilityBadge level={data.reliability} />}
                {data && <span>· {unitLabelStr}</span>}
                {data && (
                  <DirectionBadge higherIsBetter={data.higher_is_better} />
                )}
              </div>
            </div>
            {data?.sex_split && (
              <SexToggle
                value={sexChoice}
                onChange={onSexChange}
                className="shrink-0"
              />
            )}
          </div>
        </CardHeader>
        <CardContent className="px-4 sm:px-6">
          {body}
          {table}
        </CardContent>
      </Card>
    </motion.div>
  );
}

function provTitle(p: Provenance): string {
  return [p.provider, p.sourceRef, p.citation].filter(Boolean).join(" · ");
}

/* --------------------------------- Tooltips --------------------------------- */

interface TooltipEntry {
  dataKey?: string | number;
  name?: string | number;
  value?: number | string;
  color?: string;
  payload?: unknown;
}

function ProvenanceLines({ prov, witness }: { prov: Provenance; witness?: boolean }) {
  const lines: string[] = [];
  if (prov.provider) {
    lines.push(
      witness
        ? [prov.provider, prov.rootLabel].filter(Boolean).join(" · ")
        : [prov.provider, prov.sourceRef].filter(Boolean).join(" · "),
    );
  }
  if (!witness && prov.citation) lines.push(`“${trunc(prov.citation)}”`);
  if (lines.length === 0) return null;
  return (
    <div className="mt-0.5 space-y-0.5 text-[10px] leading-snug text-muted-foreground">
      {lines.map((l, i) => (
        <div key={i} className={i > 0 ? "italic" : undefined}>
          {l}
        </div>
      ))}
    </div>
  );
}

function YearTooltip({
  active,
  payload,
  unit,
  unitLabelStr,
  lang,
}: {
  active?: boolean;
  payload?: TooltipEntry[];
  unit: string;
  unitLabelStr: string;
  lang: Lang;
}) {
  if (!active || !payload || payload.length === 0) return null;
  const row = payload[0].payload as YearRow | undefined;
  if (!row) return null;

  const entries: {
    key: string;
    label: string;
    value: number | null;
    color: string;
    dashed?: boolean;
    faded?: boolean;
    prov: Provenance;
    witness?: boolean;
  }[] = [];

  if (row.value !== null) {
    entries.push({
      key: "value",
      label: "",
      value: row.value,
      color: row.color,
      prov: row.prov,
    });
  }
  if (row.valueM !== null) {
    entries.push({
      key: "valueM",
      label: "M · ",
      value: row.valueM,
      color: row.color,
      prov: row.provM,
    });
  }
  if (row.valueF !== null) {
    entries.push({
      key: "valueF",
      label: "F · ",
      value: row.valueF,
      color: row.color,
      faded: true,
      prov: row.provF,
    });
  }
  if (row.witness !== null) {
    entries.push({
      key: "witness",
      label: "",
      value: row.witness,
      color: row.color,
      dashed: true,
      prov: row.wprov,
      witness: true,
    });
  }

  return (
    <div className="max-w-72 rounded-lg border bg-popover px-3 py-2 text-xs text-popover-foreground shadow-md">
      <div className="mb-1.5 font-semibold">{row.label}</div>
      <div className="space-y-1.5">
        {entries.map((e) => (
          <div key={e.key}>
            <div className="flex items-center justify-between gap-4">
              <span className="inline-flex items-center gap-1.5 text-muted-foreground">
                <span
                  aria-hidden
                  className="inline-block w-4"
                  style={{
                    borderTop: e.dashed
                      ? `2px dashed ${e.color}`
                      : undefined,
                    background: e.dashed
                      ? undefined
                      : e.color,
                    height: e.dashed ? 0 : 8,
                    borderRadius: 2,
                    opacity: e.faded ? 0.55 : 1,
                  }}
                />
                {e.label}
              </span>
              <span className="tnum font-medium">
                {e.value !== null
                  ? `${fmtNumber(e.value, unit, lang)} ${unitLabelStr}`.trim()
                  : ""}
              </span>
            </div>
            <ProvenanceLines prov={e.prov} witness={e.witness} />
          </div>
        ))}
      </div>
    </div>
  );
}

function PeriodTooltip({
  active,
  payload,
  defs,
  labels,
  countries,
  unit,
  unitLabelStr,
  lang,
}: {
  active?: boolean;
  payload?: TooltipEntry[];
  defs: PeriodDef[];
  labels: Map<string, string>;
  countries: string[];
  unit: string;
  unitLabelStr: string;
  lang: Lang;
}) {
  if (!active || !payload || payload.length === 0) return null;
  const row = payload[0].payload as PeriodRow | undefined;
  if (!row) return null;
  const year = row.year;

  const entries = defs
    .map((d) => {
      const v = row[d.key];
      if (typeof v !== "number") return null;
      const witness = d.witness === true;
      const prov: Provenance = witness
        ? {
            provider: String(row[`p_${d.key}`] ?? ""),
            rootLabel: String(row[`rl_${d.key}`] ?? ""),
          }
        : {
            provider: String(row[`p_${d.key}`] ?? ""),
            sourceRef: String(row[`r_${d.key}`] ?? ""),
            citation: row[`c_${d.key}`] ? String(row[`c_${d.key}`]) : undefined,
          };
      const color = colorForIndex(countries.indexOf(d.entityId));
      return {
        key: d.key,
        label: `${
          labels.get(d.entityId) ?? d.entityId
        }${d.sex ? ` · ${d.sex === "male" ? "M" : "F"}` : ""}${
          witness ? ` · ${String(row[`rl_${d.key}`] ?? "")}` : ""
        }`,
        value: v,
        color,
        dashed: witness || d.sex === "female",
        faded: d.sex === "female" && !witness,
        prov,
        witness,
      };
    })
    .filter((e): e is NonNullable<typeof e> => e !== null);

  return (
    <div className="max-w-80 rounded-lg border bg-popover px-3 py-2 text-xs text-popover-foreground shadow-md">
      <div className="mb-1.5 font-semibold tnum">{year}</div>
      <div className="slim-scroll max-h-72 space-y-1.5 overflow-y-auto">
        {entries.map((e) => (
          <div key={e.key}>
            <div className="flex items-center justify-between gap-4">
              <span className="inline-flex min-w-0 items-center gap-1.5 text-muted-foreground">
                <span
                  aria-hidden
                  className="inline-block w-4 shrink-0"
                  style={{
                    borderTop: e.dashed ? `2px dashed ${e.color}` : undefined,
                    background: e.dashed ? undefined : e.color,
                    height: e.dashed ? 0 : 8,
                    borderRadius: 2,
                    opacity: e.faded ? 0.55 : 1,
                  }}
                />
                <span className="truncate">{e.label}</span>
              </span>
              <span className="tnum font-medium">
                {`${fmtNumber(e.value, unit, lang)} ${unitLabelStr}`.trim()}
              </span>
            </div>
            <ProvenanceLines prov={e.prov} witness={e.witness} />
          </div>
        ))}
      </div>
    </div>
  );
}

// Period tooltip receives the selection order to resolve country colors.

/* --------------------------------- Legend --------------------------------- */

function LegendSwatch({
  label,
  color,
  kind,
  faded,
}: {
  label: string;
  color: string;
  kind: "solid" | "dashed" | "dotted" | "ghost" | "dot";
  faded?: boolean;
}) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        aria-hidden
        className={
          kind === "dot"
            ? "inline-block h-2 w-2 rounded-full"
            : kind === "ghost"
              ? "inline-block h-2.5 w-5 rounded-[3px] border border-dashed"
              : "inline-block w-5"
        }
        style={
          kind === "dot"
            ? { background: color }
            : kind === "ghost"
              ? { background: color, opacity: 0.3 }
              : {
                  borderTop:
                    kind === "dashed"
                      ? `2px dashed ${color}`
                      : kind === "dotted"
                        ? `2px dotted ${color}`
                        : undefined,
                  background: kind === "solid" ? color : undefined,
                  height: kind === "solid" ? 8 : 0,
                  borderRadius: 2,
                  opacity: faded ? 0.55 : 1,
                }
        }
      />
      {label}
    </span>
  );
}
