"use client";

import { ArrowUpRight, Search } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";
import {
  DirectionBadge,
  FamilyBadge,
  ReliabilityBadge,
  ToddCoreBadge,
} from "@/components/shared/badges";
import { PageHeader } from "@/components/shared/page-header";
import { ErrorBlock } from "@/components/shared/states";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useCatalog } from "@/lib/toddlab/client";
import { interpolate, useFamilyLabel, useI18n, useIndicatorLabel } from "@/lib/toddlab/i18n";
import { cn } from "@/lib/utils";

export function CatalogView() {
  const { t } = useI18n();
  const indicatorLabel = useIndicatorLabel();
  const familyLabel = useFamilyLabel();
  const { data, isLoading, isError, refetch } = useCatalog();

  const [query, setQuery] = useState("");
  const [family, setFamily] = useState<string | null>(null);
  const [toddOnly, setToddOnly] = useState(false);

  const families = useMemo(() => {
    const set = new Set((data?.indicators ?? []).map((i) => i.family));
    return [...set].sort((a, b) => familyLabel(a).localeCompare(familyLabel(b)));
  }, [data, familyLabel]);

  const indicators = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (data?.indicators ?? [])
      .filter((i) => (family === null ? true : i.family === family))
      .filter((i) => (toddOnly ? i.todd_core : true))
      .filter((i) => {
        if (!q) return true;
        return (
          indicatorLabel(i.id, i.label).toLowerCase().includes(q) ||
          i.id.includes(q) ||
          familyLabel(i.family).toLowerCase().includes(q)
        );
      })
      .sort((a, b) =>
        indicatorLabel(a.id, a.label).localeCompare(indicatorLabel(b.id, b.label)),
      );
  }, [data, family, toddOnly, query, indicatorLabel, familyLabel]);

  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6">
      <PageHeader
        title={t((d) => d.indicators.title)}
        subtitle={interpolate(t((d) => d.indicators.subtitle), {
          n: data ? data.indicators.filter((i) => i.todd_core).length : "…",
        })}
      />

      {/* Toolbar */}
      <div className="mb-6 space-y-3">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t((d) => d.indicators.searchPlaceholder)}
              className="pl-9"
              aria-label={t((d) => d.indicators.searchPlaceholder)}
            />
          </div>
          <div className="flex items-center gap-2">
            <Switch
              id="todd-only"
              checked={toddOnly}
              onCheckedChange={setToddOnly}
              aria-label={t((d) => d.indicators.toddOnly)}
            />
            <Label
              htmlFor="todd-only"
              className="cursor-pointer text-sm text-muted-foreground"
            >
              {t((d) => d.indicators.toddOnly)}
            </Label>
          </div>
        </div>

        <div
          className="flex flex-wrap items-center gap-1.5"
          role="group"
          aria-label={t((d) => d.common.family)}
        >
          <button
            type="button"
            onClick={() => setFamily(null)}
            aria-pressed={family === null}
            className={cn(
              "rounded-full border px-3 py-1 text-xs transition-colors",
              family === null
                ? "border-primary bg-primary text-primary-foreground"
                : "border-border bg-card text-muted-foreground hover:bg-accent hover:text-foreground",
            )}
          >
            {t((d) => d.indicators.familyAll)}
          </button>
          {families.map((f) => (
            <button
              key={f}
              type="button"
              onClick={() => setFamily(family === f ? null : f)}
              aria-pressed={family === f}
              className={cn(
                "rounded-full border px-3 py-1 text-xs transition-colors",
                family === f
                  ? "border-primary bg-primary text-primary-foreground"
                  : "border-border bg-card text-muted-foreground hover:bg-accent hover:text-foreground",
              )}
            >
              {familyLabel(f)}
            </button>
          ))}
        </div>
      </div>

      {/* Grid */}
      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-44 rounded-xl" />
          ))}
        </div>
      ) : isError ? (
        <ErrorBlock onRetry={() => refetch()} />
      ) : indicators.length === 0 ? (
        <p className="py-16 text-center text-sm text-muted-foreground">
          {t((d) => d.common.noData)}
        </p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {indicators.map((item) => {
            const label = indicatorLabel(item.id, item.label);
            if (!item.available) {
              return (
                <TooltipProvider key={item.id} delayDuration={200}>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <div
                        aria-disabled
                        className="cursor-default rounded-xl opacity-60"
                      >
                        <IndicatorCardBody item={item} label={label} unavailable />
                      </div>
                    </TooltipTrigger>
                    <TooltipContent className="max-w-72 text-xs">
                      {t((d) => d.indicators.unavailableTitle)}
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              );
            }
            return (
              <Link
                key={item.id}
                href={`/indicators/${item.id}`}
                className="group rounded-xl focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
                aria-label={t((d) => d.common.seeIndicator)}
              >
                <IndicatorCardBody item={item} label={label} />
              </Link>
            );
          })}
        </div>
      )}
    </main>
  );
}

type CatalogEntry = NonNullable<
  ReturnType<typeof useCatalog>["data"]
>["indicators"][number];

function IndicatorCardBody({
  item,
  label,
  unavailable = false,
}: {
  item: CatalogEntry;
  label: string;
  unavailable?: boolean;
}) {
  const { t } = useI18n();
  return (
    <Card
      className={cn(
        "h-full gap-3 transition-shadow",
        !unavailable &&
          "group-hover:shadow-md group-hover:ring-1 group-hover:ring-primary/30",
      )}
    >
      <CardContent className="flex h-full flex-col gap-3">
        <div className="flex items-start justify-between gap-2">
          <h2 className="font-serif-display text-base font-semibold leading-snug">
            {label}
          </h2>
          {unavailable ? (
            <Badge variant="secondary" className="shrink-0">
              N/A
            </Badge>
          ) : (
            <ArrowUpRight className="mt-0.5 h-4 w-4 shrink-0 text-primary opacity-0 transition-opacity group-hover:opacity-100" />
          )}
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          <FamilyBadge family={item.family} />
          {item.todd_core && <ToddCoreBadge />}
          {item.reliability !== "high" && (
            <ReliabilityBadge level={item.reliability} />
          )}
        </div>
        <div className="mt-auto space-y-1.5">
          <DirectionBadge higherIsBetter={item.higher_is_better} />
          <p className="text-xs text-muted-foreground">
            <span className="tnum">{item.n_points}</span>{" "}
            {t((d) => d.common.points)}
            {item.todd_refs && (
              <>
                {" · "}
                <span className="tnum">{item.todd_refs.citations}</span>{" "}
                {t((d) => d.indicators.citations)}
                {" · "}
                <span className="tnum">{item.todd_refs.books}</span>{" "}
                {t((d) => d.indicators.books)}
              </>
            )}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
