"use client";

import * as React from "react";
import Link from "next/link";
import { ArrowDownRight, ArrowUpRight, TrendingUp } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorBlock, LoadingBlock } from "@/components/shared/states";
import { interpolate, useEntityLabel, useI18n } from "@/lib/toddlab/i18n";
import { useEntities, useScoreMovers } from "@/lib/toddlab/client";
import { fmtScore } from "@/lib/toddlab/format";
import type {
  ScoreMoverRow,
  ScoreName,
  StoredPreset,
} from "@/lib/toddlab/score-types";
import { cn } from "@/lib/utils";

const PAGE = 10;
const MAX = 40;

function signed(value: number, lang: "fr" | "en"): string {
  const s = fmtScore(Math.abs(value), lang);
  return value > 0 ? `+${s}` : value < 0 ? `−${s}` : s;
}

function YearSelect({
  label,
  value,
  years,
  onChange,
}: {
  label: string;
  value: number;
  years: number[];
  onChange: (y: number) => void;
}) {
  return (
    <label className="inline-flex items-center gap-2 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(Number.parseInt(e.target.value, 10))}
        className="tnum rounded-md border bg-background px-2 py-1 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        {years.map((y) => (
          <option key={y} value={y}>
            {y}
          </option>
        ))}
      </select>
    </label>
  );
}

function MoversColumn({
  title,
  rows,
  tone,
  labelOf,
  maxAbs,
}: {
  title: string;
  rows: ScoreMoverRow[];
  tone: "up" | "down";
  labelOf: (id: string) => string;
  maxAbs: number;
}) {
  const { t, lang } = useI18n();
  const [expanded, setExpanded] = React.useState(false);
  const shown = rows.slice(0, expanded ? MAX : PAGE);
  const Icon = tone === "up" ? ArrowUpRight : ArrowDownRight;
  return (
    <div className="min-w-0 space-y-2">
      <h4 className="flex items-center gap-1.5 text-sm font-medium">
        <Icon
          className={cn("h-4 w-4", tone === "up" ? "text-emerald-600" : "text-orange-600")}
          aria-hidden
        />
        {title}
      </h4>
      <ol className="divide-y rounded-lg border">
        {shown.map((r, i) => (
          <li key={r.entity_id} className="grid grid-cols-[1.5rem_minmax(0,1fr)_auto] items-center gap-x-3 px-3 py-2 text-sm">
            <span className="tnum text-xs text-muted-foreground">{i + 1}</span>
            <div className="min-w-0">
              <Link
                href={`/countries/${r.entity_id}`}
                className="truncate font-medium hover:underline"
              >
                {labelOf(r.entity_id)}
              </Link>
              <div className="tnum text-xs text-muted-foreground">
                {fmtScore(r.score_from, lang)} → {fmtScore(r.score_to, lang)} ·{" "}
                {interpolate(t((d) => d.score.moversComponents), { n: String(r.n_components) })}
              </div>
              {Math.sign(r.score_to - r.score_from) !== Math.sign(r.delta) ||
              Math.abs(r.score_to - r.score_from - r.delta) > 2 ? (
                <div
                  className="text-xs text-amber-700 dark:text-amber-400"
                  title={t((d) => d.score.moversMixedTip)}
                >
                  ⚠ {t((d) => d.score.moversMixed)}
                </div>
              ) : null}
              <div
                aria-hidden
                className="mt-1 h-1 rounded-full bg-muted"
                title={signed(r.delta, lang)}
              >
                <div
                  className={cn("h-full rounded-full", tone === "up" ? "bg-emerald-600/70" : "bg-orange-600/70")}
                  style={{ width: `${Math.min(100, (Math.abs(r.delta) / Math.max(maxAbs, 0.01)) * 100)}%` }}
                />
              </div>
            </div>
            <span
              className={cn(
                "tnum text-right text-base font-semibold",
                r.delta > 0 ? "text-emerald-700 dark:text-emerald-400" : r.delta < 0 ? "text-orange-700 dark:text-orange-400" : "",
              )}
            >
              {signed(r.delta, lang)}
            </span>
          </li>
        ))}
      </ol>
      {rows.length > PAGE && (
        <button
          type="button"
          onClick={() => setExpanded((e) => !e)}
          className="text-xs text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
        >
          {expanded ? t((d) => d.score.moversShowLess) : t((d) => d.score.moversShowMore)}
        </button>
      )}
    </div>
  );
}

export function ScoreMovers({
  score,
  preset,
  from,
  to,
  onChange,
}: {
  score: ScoreName;
  preset: StoredPreset;
  from: number | null;
  to: number | null;
  onChange: (from: number, to: number) => void;
}) {
  const { t } = useI18n();
  const entityLabel = useEntityLabel();
  const entities = useEntities();
  const q = useScoreMovers(score, preset, from, to);
  const labelOf = React.useCallback(
    (id: string) => entityLabel(id, entities.data?.entities.find((e) => e.entity_id === id)?.label),
    [entityLabel, entities.data],
  );

  const data = q.data;
  // Gains = strictly positive deltas, best first; drops = strictly negative,
  // worst first. The two columns never share a country.
  const best = React.useMemo(
    () => (data ? data.rows.filter((r) => r.delta > 0).slice(0, MAX) : []),
    [data],
  );
  const worst = React.useMemo(
    () => (data ? [...data.rows].reverse().filter((r) => r.delta < 0).slice(0, MAX) : []),
    [data],
  );
  const maxAbs = data ? Math.max(0, ...data.rows.map((r) => Math.abs(r.delta))) : 0;

  return (
    <Card className="mt-6">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 font-serif-display text-lg">
          <TrendingUp className="h-4 w-4 text-primary" aria-hidden />
          {t((d) => d.score.moversTitle)}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 pt-0">
        <p className="max-w-3xl text-xs leading-relaxed text-muted-foreground">
          {t((d) => d.score.moversHint)}
        </p>
        {q.isError ? (
          <ErrorBlock onRetry={() => q.refetch()} className="min-h-48" />
        ) : !data ? (
          <LoadingBlock label={t((d) => d.common.loading)} className="min-h-48" />
        ) : (
          <>
            <div className="flex flex-wrap items-center gap-4">
              <YearSelect
                label={t((d) => d.score.moversFrom)}
                value={data.from}
                years={data.years.filter((y) => y < data.to)}
                onChange={(y) => onChange(y, data.to)}
              />
              <YearSelect
                label={t((d) => d.score.moversTo)}
                value={data.to}
                years={data.years.filter((y) => y > data.from)}
                onChange={(y) => onChange(data.from, y)}
              />
            </div>
            {data.rows.length === 0 ? (
              <p className="rounded-lg border border-dashed px-4 py-8 text-center text-sm text-muted-foreground">
                {t((d) => d.score.moversEmpty)}
              </p>
            ) : (
              <div className="grid gap-6 md:grid-cols-2">
                <MoversColumn
                  title={t((d) => d.score.moversBest)}
                  rows={best}
                  tone="up"
                  labelOf={labelOf}
                  maxAbs={maxAbs}
                />
                <MoversColumn
                  title={t((d) => d.score.moversWorst)}
                  rows={worst}
                  tone="down"
                  labelOf={labelOf}
                  maxAbs={maxAbs}
                />
              </div>
            )}
            {data.n_refused > 0 && (
              <p className="text-xs text-muted-foreground">
                {interpolate(t((d) => d.score.moversLeftOut), {
                  n: String(data.n_refused),
                  m: String(data.n_scored_both),
                })}
              </p>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
