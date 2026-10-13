"use client";

import { motion } from "framer-motion";
import { Search, TriangleAlert } from "lucide-react";
import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { PageHeader } from "@/components/shared/page-header";
import { ErrorBlock, LoadingBlock } from "@/components/shared/states";
import { useEntities, type EntityItem } from "@/lib/toddlab/client";
import { useEntityLabel, useI18n } from "@/lib/toddlab/i18n";
import { cn } from "@/lib/utils";

function EntityCard({
  entity,
  index,
}: {
  entity: EntityItem;
  index: number;
}) {
  const entityLabel = useEntityLabel();
  const { lang } = useI18n();

  const metricsLabel =
    entity.n_indicators_with_data > 0
      ? lang === "fr"
        ? `${entity.n_indicators_with_data} métriques`
        : `${entity.n_indicators_with_data} metrics`
        : "-";

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, delay: Math.min(index * 0.015, 0.4) }}
    >
      <a
        href={`/countries/${entity.entity_id}`}
        className="group block h-full rounded-xl border bg-card p-4 transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <div className="flex items-start justify-between gap-2">
          <span className="font-medium leading-tight group-hover:text-primary transition-colors">
            {entityLabel(entity.entity_id, entity.label)}
          </span>
          {entity.iso3 && (
            <span className="tnum text-xs text-muted-foreground shrink-0">
              {entity.iso3}
            </span>
          )}
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-1.5">
          {entity.formerly_part_of && (
            <Badge
              variant="outline"
              className="gap-1 border-amber-500/40 bg-amber-500/5 text-amber-700 dark:text-amber-400"
            >
              <TriangleAlert className="h-3 w-3" />
              {entity.formerly_part_of.union_entity_id === "ussr"
                ? lang === "fr"
                  ? "ex-URSS"
                  : "ex-USSR"
                : `ex-${entity.formerly_part_of.union_entity_id}`}
            </Badge>
          )}
          {(entity.valid_to !== null || entity.valid_from !== null) && (
            <Badge variant="outline" className="font-normal text-muted-foreground">
              {entityLabel("historical", "Historical")}
            </Badge>
          )}
          <Badge
            variant="secondary"
            className={cn(
              "font-normal tnum",
              entity.n_indicators_with_data === 0 && "text-muted-foreground/50",
            )}
          >
            {metricsLabel}
          </Badge>
        </div>
      </a>
    </motion.div>
  );
}

export function CountriesView() {
  const { t, lang } = useI18n();
  const entityLabel = useEntityLabel();
  const { data, isLoading, isError, refetch } = useEntities();
  const [query, setQuery] = React.useState("");
  const [withDataOnly, setWithDataOnly] = React.useState(false);

  const entities = React.useMemo(() => {
    const list = data?.entities ?? [];
    const q = query.trim().toLowerCase();
    return list
      .filter((e) => {
        if (withDataOnly && e.n_indicators_with_data === 0) return false;
        if (!q) return true;
        return (
          entityLabel(e.entity_id, e.label).toLowerCase().includes(q) ||
          e.entity_id.includes(q) ||
          (e.iso3 ?? "").toLowerCase().includes(q)
        );
      })
      .sort(
        (a, b) =>
          b.n_indicators_with_data - a.n_indicators_with_data ||
          entityLabel(a.entity_id, a.label).localeCompare(
            entityLabel(b.entity_id, b.label),
          ),
      );
  }, [data, query, withDataOnly, entityLabel]);

  const total = data?.entities.length ?? 0;

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
      <PageHeader
        title={t((d) => d.countries.title)}
        subtitle={t((d) => d.countries.subtitle)}
      >
        <div className="flex flex-col gap-3 pt-2 sm:flex-row sm:items-center">
          <div className="relative max-w-sm flex-1">
            <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t((d) => d.countries.searchPlaceholder)}
              className="pl-8"
              aria-label={t((d) => d.common.search)}
            />
          </div>
          <div className="flex items-center gap-2">
            <Switch
              id="with-data"
              checked={withDataOnly}
              onCheckedChange={setWithDataOnly}
            />
            <Label htmlFor="with-data" className="text-sm text-muted-foreground">
              {t((d) => d.countries.withDataOnly)}
            </Label>
          </div>
          <span className="tnum ml-auto text-sm text-muted-foreground">
            {entities.length} / {total}
          </span>
        </div>
      </PageHeader>

      {isLoading ? (
        <LoadingBlock label={t((d) => d.common.loading)} className="min-h-64" />
      ) : isError ? (
        <ErrorBlock onRetry={() => refetch()} />
      ) : entities.length === 0 ? (
        <p className="py-16 text-center text-sm text-muted-foreground">
          {t((d) => d.common.noData)}
        </p>
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
          {entities.map((e, i) => (
            <EntityCard key={e.entity_id} entity={e} index={i} />
          ))}
        </div>
      )}
    </div>
  );
}
