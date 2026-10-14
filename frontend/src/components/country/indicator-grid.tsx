"use client";

import { motion } from "framer-motion";
import { Scale } from "lucide-react";
import Link from "next/link";
import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { ReliabilityBadge, ToddCoreBadge } from "@/components/shared/badges";
import { Sparkline } from "@/components/shared/sparkline";
import type { CountryProfile } from "@/lib/toddlab/client";
import {
  useFamilyLabel,
  useI18n,
  useIndicatorLabel,
  useUnitLabel,
} from "@/lib/toddlab/i18n";
import { fmtNumber } from "@/lib/toddlab/format";

const FAMILY_ORDER = [
  "mortality",
  "society",
  "economy",
  "education",
  "demography",
  "markers",
];

type ProfileIndicator = CountryProfile["indicators"][number];

function IndicatorCard({
  ind,
  countryId,
  index,
}: {
  ind: ProfileIndicator;
  countryId: string;
  index: number;
}) {
  const { t, lang } = useI18n();
  const indicatorLabel = useIndicatorLabel();
  const unitLabel = useUnitLabel();
  const familyLabel = useFamilyLabel();

  const hasData =
    ind.last_value !== null && ind.last_value !== undefined && ind.last_year !== null;

  const sparkValues: (number | null)[] = React.useMemo(() => {
    if (ind.sex_series) {
      // Merge both sexes on a shared year axis — gaps stay gaps
      const years = new Set<number>();
      ind.sex_series.male.forEach((p) => years.add(p.year));
      ind.sex_series.female.forEach((p) => years.add(p.year));
      const m = new Map(ind.sex_series.male.map((p) => [p.year, p.value]));
      const f = new Map(ind.sex_series.female.map((p) => [p.year, p.value]));
      return [...years].sort((a, b) => a - b).map((y) => m.get(y) ?? f.get(y) ?? null);
    }
    return ind.series.map((p) => p.value);
  }, [ind]);

  const compareHref = `/compare?c=${countryId}&m=${ind.id}`;

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-40px" }}
      transition={{ duration: 0.22, delay: Math.min((index % 6) * 0.03, 0.2) }}
      className="group relative flex h-full flex-col rounded-xl border bg-card p-4 transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-sm"
    >
      <div className="flex items-start justify-between gap-2">
        <Link
          href={`/indicators/${ind.id}?country=${countryId}`}
          className="text-sm font-medium leading-snug hover:text-primary transition-colors"
        >
          {indicatorLabel(ind.id, ind.label)}
        </Link>
        {ind.todd_core && <ToddCoreBadge compact />}
      </div>

      <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
        <Badge variant="outline" className="font-normal text-muted-foreground">
          {familyLabel(ind.family)}
        </Badge>
        {ind.reliability !== "high" && <ReliabilityBadge level={ind.reliability} />}
      </div>

      <div className="mt-3 flex items-end justify-between gap-2">
        {hasData ? (
          <div className="min-w-0">
            <div className="tnum text-2xl font-semibold tracking-tight">
              {fmtNumber(ind.last_value, ind.unit, lang)}
              <span className="ml-1 text-sm font-normal text-muted-foreground">
                {unitLabel(ind.unit)}
              </span>
            </div>
            <div className="mt-0.5 text-xs text-muted-foreground">
              {ind.last_year}
              {ind.last_sex && (
                <span className="ml-1">
                  · {ind.last_sex === "male" ? (lang === "fr" ? "H" : "M") : "F"}
                </span>
              )}
            </div>
          </div>
        ) : (
          <div className="text-sm text-muted-foreground/60">-</div>
        )}
        <div className="flex flex-col items-end gap-1.5 shrink-0">
          {sparkValues.filter((v) => v !== null).length >= 2 && (
            <Sparkline
              values={sparkValues}
              color={ind.sex_series ? "var(--chart-6)" : "var(--primary)"}
            />
          )}
          {ind.rank !== null && ind.n_ranked ? (
            <TooltipProvider delayDuration={200}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Badge variant="outline" className="tnum font-normal cursor-help">
                    {t((d) => d.common.rank)} {ind.rank}
                    <span className="text-muted-foreground">/{ind.n_ranked}</span>
                    {ind.rank_basis === "witness" && <span>*</span>}
                  </Badge>
                </TooltipTrigger>
                <TooltipContent className="text-xs">
                  {ind.rank_basis === "witness" && ind.witness_root_label
                    ? `${t((d) => d.common.basedOnWitness)} · ${ind.witness_root_label}`
                    : ind.canonical_nature === "modelled"
                      ? t((d) => d.common.witness)
                      : t((d) => d.common.canonical)}
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          ) : null}
        </div>
      </div>

      <div className="mt-3 flex items-center justify-end gap-1 sm:opacity-0 sm:transition-opacity sm:group-hover:opacity-100 sm:focus-within:opacity-100">
        <Button asChild variant="ghost" size="sm" className="h-7 gap-1.5 text-xs">
          <Link href={compareHref}>
            <Scale className="h-3 w-3" />
            {lang === "fr" ? "Comparer" : "Compare"}
          </Link>
        </Button>
      </div>
    </motion.div>
  );
}

export function IndicatorGrid({
  indicators,
  countryId,
}: {
  indicators: CountryProfile["indicators"];
  countryId: string;
}) {
  const { t } = useI18n();
  const familyLabel = useFamilyLabel();

  const groups = React.useMemo(() => {
    const map = new Map<string, ProfileIndicator[]>();
    for (const ind of indicators) {
      const arr = map.get(ind.family) ?? [];
      arr.push(ind);
      map.set(ind.family, arr);
    }
    return FAMILY_ORDER.filter((f) => map.has(f)).map((f) => ({
      family: f,
      items: map.get(f)!,
    }));
  }, [indicators]);

  return (
    <div className="space-y-10">
      {groups.map(({ family, items }) => (
        <section key={family} aria-label={familyLabel(family)}>
          <h2 className="mb-4 font-serif-display text-lg font-semibold tracking-tight">
            {familyLabel(family)}
          </h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {items.map((ind, i) => (
              <IndicatorCard
                key={ind.id}
                ind={ind}
                countryId={countryId}
                index={i}
              />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
