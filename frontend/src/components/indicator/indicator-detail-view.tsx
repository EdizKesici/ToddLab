"use client";

import { Globe, Repeat2 } from "lucide-react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { IndicatorSeriesCard } from "@/components/indicator/indicator-series-card";
import { RankingTable } from "@/components/indicator/ranking-table";
import { WorldMap } from "@/components/indicator/world-map";
import { useIndicatorQueryState } from "@/components/indicator/use-indicator-query-state";
import {
  DirectionBadge,
  FamilyBadge,
  ReliabilityBadge,
  ToddCoreBadge,
} from "@/components/shared/badges";
import { PageHeader } from "@/components/shared/page-header";
import { type SexChoice } from "@/components/shared/sex-toggle";
import { EmptyBlock, ErrorBlock, LoadingBlock } from "@/components/shared/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  useCatalog,
  useEntities,
  useIndicatorMeta,
  useYearData,
  type CatalogItem,
  type IndicatorMetaPayload,
  type YearPayload,
} from "@/lib/toddlab/client";
import { fmtNumber } from "@/lib/toddlab/format";
import {
  useEntityLabel,
  useI18n,
  useIndicatorDescription,
  useIndicatorLabel,
  useProviderLabel,
  useUnitLabel,
} from "@/lib/toddlab/i18n";

type ToddRefs = NonNullable<IndicatorMetaPayload["todd_refs"]>;

/** Default series selection when no ?c= is present and no focus country. */
const DEFAULT_COUNTRIES = [
  "france",
  "united_states",
  "russian_federation",
  "japan",
];

export default function IndicatorDetailView() {
  return (
    <Suspense fallback={<DetailRouteFallback />}>
      <IndicatorDetailRoute />
    </Suspense>
  );
}

function DetailRouteFallback() {
  const { t } = useI18n();
  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6">
      <LoadingBlock label={t((d) => d.common.loading)} />
    </main>
  );
}

function IndicatorDetailRoute() {
  const params = useParams<{ id: string | string[] }>();
  const id = Array.isArray(params.id) ? params.id[0] : params.id;
  // ?country=<entity_id> — arrival from a country profile: the page leads
  // with that country's own value (FocusBand) instead of the world view.
  // Full view state (year, sex, series selection, estimates) also lives in
  // the URL — see use-indicator-query-state.
  const searchParams = useSearchParams();
  const focusRaw = searchParams.get("country");
  const focusEntityId = focusRaw && focusRaw.trim() !== "" ? focusRaw.trim() : null;

  const { t } = useI18n();
  const indicatorLabel = useIndicatorLabel();
  const indicatorDescription = useIndicatorDescription();

  const { data: catalogData } = useCatalog();
  const catalogItem = catalogData?.indicators.find((i) => i.id === id);

  const {
    data: meta,
    isLoading,
    error,
    refetch,
  } = useIndicatorMeta(id ?? null);
  const status = (error as (Error & { status?: number }) | null)?.status;

  const headerLabel = id
    ? indicatorLabel(id, meta?.label ?? catalogItem?.label ?? id)
    : "";
  const description = id ? indicatorDescription(id) : null;

  /* --------------------------------- States --------------------------------- */
  if (isLoading || (!meta && !error)) {
    return (
      <main className="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6">
        <LoadingBlock label={t((d) => d.common.loading)} />
      </main>
    );
  }

  if (status === 404) {
    return (
      <main className="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6">
        <EmptyBlock message={t((d) => d.common.noData)} />
      </main>
    );
  }

  if (status === 503) {
    return (
      <main className="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6">
        <PageHeader title={headerLabel}>
          <div className="flex flex-wrap items-center gap-2">
            {catalogItem && <FamilyBadge family={catalogItem.family} />}
            <Badge variant="secondary">N/A</Badge>
          </div>
          {description && (
            <p className="max-w-3xl text-sm leading-relaxed text-muted-foreground sm:text-base">
              {description}
            </p>
          )}
        </PageHeader>
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-start gap-3">
            <h2 className="font-serif-display text-lg font-semibold">
              {t((d) => d.indicators.unavailableTitle)}
            </h2>
            <p className="max-w-2xl text-sm text-muted-foreground">
              {t((d) => d.indicators.unavailableText)}
            </p>
          </CardContent>
        </Card>
      </main>
    );
  }

  if (!meta) {
    return (
      <main className="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6">
        <ErrorBlock onRetry={() => refetch()} />
      </main>
    );
  }

  // key={meta.id} resets year/sex state when navigating between indicators.
  return (
    <DetailContent
      key={meta.id}
      meta={meta}
      catalogItem={catalogItem ?? null}
      focusEntityId={focusEntityId}
    />
  );
}

/* -------------------------------- Content --------------------------------- */

function DetailContent({
  meta,
  catalogItem,
  focusEntityId,
}: {
  meta: IndicatorMetaPayload;
  catalogItem: CatalogItem | null;
  focusEntityId: string | null;
}) {
  const { t } = useI18n();
  const indicatorLabel = useIndicatorLabel();
  const indicatorDescription = useIndicatorDescription();
  const unitLabel = useUnitLabel();

  // Default series selection: the focused country, else the classic four.
  const initialCountries = focusEntityId ? [focusEntityId] : DEFAULT_COUNTRIES;

  // Year / sex / series selection lifted into the URL — the map, the ranking
  // and the series card share one source, and every view is shareable.
  const { state: query, patch } = useIndicatorQueryState({
    defaultYear:
      meta.default_year ??
      (meta.available_years.length > 0
        ? meta.available_years[meta.available_years.length - 1]
        : null),
    initialCountries,
  });

  const [autoYear, setAutoYear] = useState<number | null>(null);
  const years = meta.available_years;
  // Server-computed sensible default (latest well-covered year, or the latest
  // event year for unit="year" indicators) instead of a near-empty snapshot.
  const effectiveYear =
    query.year ??
    autoYear ??
    meta.default_year ??
    years[years.length - 1] ??
    null;
  const effectiveSex = query.sex;

  // Default to the latest year, but if it carries no data at all, step back to
  // the latest year that does (the user's explicit choice always wins).
  const userAdjusted = useRef(false);
  const { data: probe } = useYearData(meta.id, effectiveYear, effectiveSex);

  useEffect(() => {
    if (userAdjusted.current || !probe || effectiveYear === null) return;
    const hasData =
      probe.points.some((p) => p.value !== null) ||
      (probe.witness_points ?? []).some((b) => b.points.some((p) => p.value !== null));
    if (hasData) return;
    const idx = years.indexOf(effectiveYear);
    if (idx <= 0) return;
    const timer = setTimeout(() => setAutoYear(years[idx - 1]), 0);
    return () => clearTimeout(timer);
  }, [probe, effectiveYear, years]);

  const handleYearChange = (y: number) => {
    userAdjusted.current = true;
    setAutoYear(y);
    patch({ year: y });
  };
  const handleSexChange = (s: SexChoice) => {
    userAdjusted.current = true;
    patch({ sex: s });
  };

  const headerLabel = indicatorLabel(meta.id, meta.label);
  const description = indicatorDescription(meta.id);

  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6">
      <PageHeader title={headerLabel}>
        <div className="flex flex-wrap items-center gap-2">
          <FamilyBadge family={meta.family} />
          {meta.todd_core && <ToddCoreBadge />}
          <ReliabilityBadge level={meta.reliability} />
          <DirectionBadge
            higherIsBetter={meta.higher_is_better}
            family={meta.family}
          />
          {meta.reclassification_sensitive && (
            <TooltipProvider delayDuration={200}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Badge
                    variant="outline"
                    className="gap-1 border-amber-500/50 text-amber-700 dark:text-amber-400"
                  >
                    <Repeat2 className="h-3 w-3" />
                    ICD
                  </Badge>
                </TooltipTrigger>
                <TooltipContent className="max-w-64 text-xs">
                  {t((d) => d.compare.reclassSensitive)}
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
        </div>
        <p className="text-sm text-muted-foreground">
          {unitLabel(meta.unit)}
          {" · "}
          <span className="tnum">
            {meta.coverage_declared.start} – {meta.coverage_declared.end}
          </span>
          {meta.todd_refs && (
            <>
              {" · "}
              <span className="tnum">{meta.todd_refs.citations}</span>{" "}
              {t((d) => d.indicators.citations)}
              {" · "}
              <span className="tnum">{meta.todd_refs.books}</span>{" "}
              {t((d) => d.indicators.books)}
            </>
          )}
        </p>
        {description && (
          <p className="max-w-3xl text-sm leading-relaxed text-muted-foreground sm:text-base">
            {description}
          </p>
        )}
      </PageHeader>

      <div className="space-y-6">
        {/* 0 — Focused country (arrival from a country profile) */}
        {focusEntityId && (
          <FocusBand
            meta={meta}
            focusId={focusEntityId}
            year={effectiveYear}
            sex={effectiveSex}
          />
        )}

        {/* 1 — World map */}
        <WorldMap
          indicatorId={meta.id}
          availableYears={meta.available_years}
          sexSplit={meta.sex_split}
          higherIsBetter={meta.higher_is_better}
          neutral={meta.family === "markers"}
          unit={meta.unit}
          year={effectiveYear}
          sex={effectiveSex}
          onYearChange={handleYearChange}
          onSexChange={handleSexChange}
          focusEntityId={focusEntityId}
        />

        {/* 2 — Ranking + 3 — Series */}
        <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
          {/* At xl the ranking absolutely fills a wrapper that contributes no
              height of its own — the row is sized by the series card, so the
              ranking table grows/shrinks to keep both cards bottom-aligned. */}
          <div className="relative">
            <div className="xl:absolute xl:inset-0">
              <RankingTable
                fill
                indicatorId={meta.id}
                unit={meta.unit}
                higherIsBetter={meta.higher_is_better}
                year={effectiveYear}
                sex={effectiveSex}
                focusEntityId={focusEntityId}
              />
            </div>
          </div>
          <IndicatorSeriesCard
            indicatorId={meta.id}
            sexSplit={meta.sex_split}
            unit={meta.unit}
            countries={query.seriesCountries ?? initialCountries}
            onCountriesChange={(c) => patch({ seriesCountries: c })}
            sex={query.seriesSex}
            onSexChange={(s) => patch({ seriesSex: s })}
            showWitness={query.witness}
            onWitnessChange={(w) => patch({ witness: w })}
            base100={query.base100 && meta.unit !== "year"}
            onBase100Change={(b) => patch({ base100: b })}
          />
        </div>

        {/* 4 — Sources */}
        <SourcesSection meta={meta} />

        {/* 5 — Todd refs */}
        {meta.todd_refs && <ToddRefsSection refs={meta.todd_refs} />}

        {/* 6 — Reliability, in one short sentence */}
        <Card>
          <CardHeader>
            <CardTitle className="font-serif-display text-lg">
              {t((d) => d.indicators.reliabilityCriteria)}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
              <ReliabilityBadge level={meta.reliability} />
              <p className="max-w-3xl text-sm text-muted-foreground">
                {meta.canonical_nature === "modelled"
                  ? t((d) => d.indicators.relModelledText)
                  : meta.reliability === "high"
                    ? t((d) => d.indicators.relHighText)
                    : meta.reliability === "medium"
                      ? t((d) => d.indicators.relMediumText)
                      : t((d) => d.indicators.relLowText)}
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}

/* ------------------------------- Focus band -------------------------------- */

interface FocusValue {
  value: number;
  rank: number | null;
  n: number | null;
  witness: boolean;
}

/**
 * The focused country's value for the current year/sex: the official figure
 * with its rank in the world distribution, or the modelled estimate as a
 * fallback (unranked, flagged). Null when the country has neither.
 */
function extractFocusValue(
  data: YearPayload | undefined,
  focusId: string,
  higherIsBetter: boolean,
): FocusValue | null {
  if (!data) return null;
  const canonical = data.points.filter((p) => p.value !== null);
  const own = canonical.find((p) => p.entity_id === focusId);
  if (own) {
    const sorted = [...canonical].sort((a, b) =>
      higherIsBetter
        ? (b.value as number) - (a.value as number)
        : (a.value as number) - (b.value as number),
    );
    return {
      value: own.value as number,
      rank: sorted.findIndex((p) => p.entity_id === focusId) + 1,
      n: sorted.length,
      witness: false,
    };
  }
  for (const block of data.witness_points ?? []) {
    const pt = block.points.find(
      (p) => p.entity_id === focusId && p.value !== null,
    );
    if (pt) {
      return { value: pt.value as number, rank: null, n: null, witness: true };
    }
  }
  return null;
}

/**
 * The user clicked a metric on a country profile: this band leads the page
 * with that country's own value, rank and reference year — and offers the
 * escape hatch to the full all-countries view. Same year-data query as the
 * map and the ranking (React Query dedupes it, no extra fetch).
 */
function FocusBand({
  meta,
  focusId,
  year,
  sex,
}: {
  meta: IndicatorMetaPayload;
  focusId: string;
  year: number | null;
  sex: SexChoice;
}) {
  const { t, lang } = useI18n();
  const entityLabel = useEntityLabel();
  const unitLabel = useUnitLabel();
  const indicatorLabel = useIndicatorLabel();
  const eventYear = meta.unit === "year";
  const { data } = useYearData(meta.id, year, sex, { byYear: eventYear });
  const { data: entitiesData } = useEntities();
  const value = extractFocusValue(data, focusId, meta.higher_is_better);
  const ent = entitiesData?.entities.find((e) => e.entity_id === focusId);
  const focusLabel = entityLabel(focusId, ent?.label);

  return (
    <Card className="border-primary/40 bg-primary/5">
      <CardHeader>
        <CardTitle className="font-serif-display text-xl">
          {focusLabel}
        </CardTitle>
        <CardDescription>
          {indicatorLabel(meta.id, meta.label)}
        </CardDescription>
        <CardAction>
          <div className="flex flex-wrap items-center gap-2">
            <Button asChild variant="ghost" size="sm">
              <Link href={`/countries/${focusId}`}>
                {t((d) => d.common.seeCountry)}
              </Link>
            </Button>
            <Button asChild size="sm" className="gap-1.5">
              <Link href={`/indicators/${meta.id}`}>
                <Globe className="h-3.5 w-3.5" />
                {t((d) => d.indicators.focusViewAll)}
              </Link>
            </Button>
          </div>
        </CardAction>
      </CardHeader>
      <CardContent>
        {value ? (
          <div className="flex flex-wrap items-end gap-x-5 gap-y-2">
            <div className="tnum text-4xl font-semibold tracking-tight">
              {fmtNumber(value.value, meta.unit, lang)}
              <span className="ml-1.5 text-sm font-normal text-muted-foreground">
                {unitLabel(meta.unit)}
              </span>
            </div>
            <div className="flex flex-col gap-0.5 pb-1 text-sm text-muted-foreground">
              <span className="tnum">
                {eventYear ? `≤ ${year ?? "?"}` : `${t((d) => d.common.year)} ${year ?? "?"}`}
                {sex !== "all" && (
                  <>
                    {" · "}
                    {sex === "male"
                      ? t((d) => d.common.male)
                      : t((d) => d.common.female)}
                  </>
                )}
              </span>
              {value.rank !== null && value.n !== null && (
                <span className="tnum">
                  {t((d) => d.common.rank)} {value.rank} / {value.n}
                </span>
              )}
            </div>
            {value.witness && (
              <Badge variant="outline" className="mb-1.5 font-normal">
                {t((d) => d.common.basedOnWitness)}
              </Badge>
            )}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">
            {t((d) => d.common.noData)}
          </p>
        )}
      </CardContent>
    </Card>
  );
}

/* ------------------------------ Sources section ----------------------------- */

/**
 * Brief, plain-language provenance: one line for the official figures,
 * one line for the modelled estimates. Full genealogy lives on GitHub.
 */
function SourcesSection({ meta }: { meta: IndicatorMetaPayload }) {
  const { t } = useI18n();
  const providerLabel = useProviderLabel();

  const canonicalProviders = [
    ...new Set(
      meta.sources
        .filter((s) => s.role === "canonical")
        .map((s) => s.provider),
    ),
  ].map(providerLabel);
  const witnessProviders = [
    ...new Set(
      meta.sources.filter((s) => s.role === "witness").map((s) => s.provider),
    ),
  ].map(providerLabel);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="font-serif-display text-lg">
          {t((d) => d.indicators.sourcesTitle)}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {canonicalProviders.length > 0 && (
          <p className="text-sm">
            <span className="font-medium">
              {meta.canonical_nature === "modelled"
                ? t((d) => d.indicators.sourcesModelledCanonical)
                : t((d) => d.indicators.sourcesOfficial)}
            </span>{" "}
            <span className="text-muted-foreground">
              {canonicalProviders.join(" · ")}
            </span>
          </p>
        )}
        {witnessProviders.length > 0 && (
          <p className="text-sm">
            <span className="font-medium">
              {t((d) => d.indicators.sourcesWitness)}
            </span>{" "}
            <span className="text-muted-foreground">
              {witnessProviders.join(" · ")}
            </span>
          </p>
        )}
      </CardContent>
    </Card>
  );
}

/* ----------------------------- Todd refs section ---------------------------- */

/**
 * Compact reading: one chip per book, with the number of times the metric
 * is cited in it. Nothing else — details live in the corpus on GitHub.
 */
function ToddRefsSection({ refs }: { refs: ToddRefs }) {
  const { t } = useI18n();
  const chips = [...refs.refs].sort((a, b) => b.citations - a.citations);
  return (
    <Card className="border-primary/30 bg-primary/5">
      <CardHeader>
        <CardTitle className="font-serif-display text-lg">
          {t((d) => d.indicators.toddRefsTitle)}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="flex flex-wrap gap-2">
          {chips.map((r, i) => (
            <li key={`${r.book}-${r.year}-${i}`}>
              <Badge
                variant="outline"
                className="border-primary/25 bg-background/60 gap-1.5 px-2.5 py-1 text-xs font-normal"
                title={`${t((d) => d.indicators.citations)}: ${r.citations}`}
              >
                <span>{r.book}</span>
                <span className="tnum text-muted-foreground">×{r.citations}</span>
              </Badge>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
