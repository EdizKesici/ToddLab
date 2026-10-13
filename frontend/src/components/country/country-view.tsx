"use client";

import { ArrowLeft, Scale, TriangleAlert } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/shared/page-header";
import { ErrorBlock, LoadingBlock } from "@/components/shared/states";
import { IndicatorGrid } from "@/components/country/indicator-grid";
import { ScoreCard } from "@/components/country/score-card";
import { useCountryProfile } from "@/lib/toddlab/client";
import { interpolate, useEntityLabel, useI18n } from "@/lib/toddlab/i18n";

export function CountryView() {
  const params = useParams<{ id: string }>();
  const id = typeof params?.id === "string" ? params.id : "";
  const { t, lang } = useI18n();
  const entityLabel = useEntityLabel();
  const { data, isLoading, isError, refetch } = useCountryProfile(id || null);

  if (isLoading) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
        <LoadingBlock label={t((d) => d.common.loading)} className="min-h-72" />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
        <ErrorBlock onRetry={() => refetch()} className="min-h-72" />
        <div className="mt-4 text-center">
          <Button asChild variant="outline" size="sm">
            <Link href="/countries">
              <ArrowLeft className="h-4 w-4" />
              {t((d) => d.countries.title)}
            </Link>
          </Button>
        </div>
      </div>
    );
  }

  const { entity, indicators } = data;
  const withData = indicators.filter(
    (i) => i.last_value !== null && i.n_points > 0,
  ).length;

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
      {/* Breadcrumb */}
      <div className="mb-4">
        <Button asChild variant="ghost" size="sm" className="-ml-2 gap-1.5 text-muted-foreground">
          <Link href="/countries">
            <ArrowLeft className="h-3.5 w-3.5" />
            {t((d) => d.countries.title)}
          </Link>
        </Button>
      </div>

      <PageHeader
        title={entityLabel(entity.entity_id, entity.label)}
        subtitle={
          <>
            {entity.iso3 && (
              <span className="tnum mr-2 inline-block rounded border px-1.5 py-0.5 text-xs align-middle">
                {entity.iso3}
              </span>
            )}
            {entity.valid_to !== null && (
              <span className="mr-3 inline-block">
                {interpolate(t((d) => d.countries.validUntil), { year: entity.valid_to })}
              </span>
            )}
            {entity.valid_from !== null && entity.valid_to === null && (
              <span className="mr-3 inline-block">
                {interpolate(t((d) => d.countries.validFrom), { year: entity.valid_from })}
              </span>
            )}
            <span className="inline-block tnum">
              {withData}/{indicators.length}{" "}
              {lang === "fr" ? "indicateurs avec données" : "indicators with data"}
            </span>
          </>
        }
      >
        <div className="flex flex-wrap items-center gap-2 pt-1">
          <Button asChild size="sm" className="gap-1.5">
            <Link href={`/compare?c=${entity.entity_id}`}>
              <Scale className="h-3.5 w-3.5" />
              {lang === "fr" ? "Comparer ce pays" : "Compare this country"}
            </Link>
          </Button>

          {entity.formerly_part_of && (
            <Badge
              variant="outline"
              className="gap-1 border-amber-500/40 bg-amber-500/5 px-2 py-1 text-amber-700 dark:text-amber-400"
            >
              <TriangleAlert className="h-3 w-3" />
              {entity.formerly_part_of.union_entity_id === "ussr"
                ? lang === "fr"
                  ? "ex-URSS"
                  : "ex-USSR"
                : `ex-${entityLabel(entity.formerly_part_of.union_entity_id)}`}
            </Badge>
          )}
        </div>

        {entity.formerly_part_of && (
          <div
            role="note"
            className="mt-4 max-w-3xl rounded-lg border border-amber-500/40 bg-amber-500/5 px-4 py-3 text-sm text-amber-800 dark:text-amber-300"
          >
            <TriangleAlert className="mr-2 inline h-4 w-4 align-[-3px]" />
            {interpolate(t((d) => d.countries.formerUnionWarning), {
              year: entity.formerly_part_of.until_year,
              union: entityLabel(entity.formerly_part_of.union_entity_id),
            })}
          </div>
        )}

        {(entity.predecessor || entity.successors.length > 0) && (
          <div className="mt-4 flex flex-wrap items-center gap-2 text-sm">
            {entity.predecessor && (
              <span className="text-muted-foreground">
                {t((d) => d.countries.predecessor)} :{" "}
                <Link
                  href={`/countries/${entity.predecessor}`}
                  className="font-medium text-foreground underline-offset-4 hover:text-primary hover:underline"
                >
                  {entityLabel(entity.predecessor)}
                </Link>
              </span>
            )}
            {entity.successors.length > 0 && (
              <span className="text-muted-foreground">
                {t((d) => d.countries.successors)} :{" "}
                {entity.successors.map((sid, i) => (
                  <React.Fragment key={sid}>
                    {i > 0 && ", "}
                    <Link
                      href={`/countries/${sid}`}
                      className="font-medium text-foreground underline-offset-4 hover:text-primary hover:underline"
                    >
                      {entityLabel(sid)}
                    </Link>
                  </React.Fragment>
                ))}
              </span>
            )}
          </div>
        )}
      </PageHeader>

      <ScoreCard entityId={entity.entity_id} />

      <div className="mt-10">
        <IndicatorGrid indicators={indicators} countryId={entity.entity_id} />
      </div>
    </div>
  );
}
