"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { type SexChoice } from "@/components/shared/sex-toggle";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useEntities, useYearData } from "@/lib/toddlab/client";
import { fmtNumber } from "@/lib/toddlab/format";
import { useEntityLabel, useI18n, useUnitLabel } from "@/lib/toddlab/i18n";
import { EmptyBlock, SkeletonRows } from "@/components/shared/states";
import { cn } from "@/lib/utils";

interface RankRow {
  entityId: string;
  rank: number;
  canonical: number | null;
  witness: number | null;
  witnessRoot: string | null;
  witnessOnly: boolean;
}

export interface RankingTableProps {
  indicatorId: string;
  unit: string;
  higherIsBetter: boolean;
  /** Year & sex are lifted to the parent page — same query key as the world map. */
  year: number | null;
  sex: SexChoice;
  /** When set (arrival from a country profile), that row is highlighted. */
  focusEntityId?: string | null;
  /**
   * Side-by-side layout mode (xl+): the card stretches to fill its wrapper,
   * which is sized by the neighbouring series card — so the scroll area grows
   * and shrinks with it instead of stopping at a fixed height. Below xl the
   * card keeps its stacked, fixed-max-height behaviour.
   */
  fill?: boolean;
}

export function RankingTable({
  indicatorId,
  unit,
  higherIsBetter,
  year,
  sex,
  focusEntityId,
  fill = false,
}: RankingTableProps) {
  const { t, lang } = useI18n();
  const entityLabel = useEntityLabel();
  const unitLabel = useUnitLabel();
  // Event-year indicators (unit "year"): the reference year acts as "by this
  // year" so the ranking lists every country whose event had occurred.
  const eventYear = unit === "year";
  const { data: yearData, isLoading } = useYearData(
    indicatorId,
    year,
    sex,
    { byYear: eventYear },
  );
  const { data: entitiesData } = useEntities();

  const labelById = useMemo(() => {
    const m = new Map<string, string>();
    for (const e of entitiesData?.entities ?? []) m.set(e.entity_id, e.label);
    return m;
  }, [entitiesData]);

  const rows = useMemo<RankRow[]>(() => {
    const canonical = (yearData?.points ?? []).filter((p) => p.value !== null);
    const witnessByEntity = new Map<string, { value: number; root: string }>();
    for (const block of yearData?.witness_points ?? []) {
      for (const p of block.points) {
        if (p.value === null) continue;
        if (!witnessByEntity.has(p.entity_id)) {
          witnessByEntity.set(p.entity_id, { value: p.value, root: block.root_label });
        }
      }
    }

    const withCanonical = new Set(canonical.map((p) => p.entity_id));
    const witnessOnly = [...witnessByEntity.entries()]
      .filter(([eid]) => !withCanonical.has(eid))
      .map(([eid, w]) => ({
        entityId: eid,
        canonical: null,
        witness: w.value,
        witnessRoot: w.root,
        witnessOnly: true,
      }));

    const all: Omit<RankRow, "rank">[] = [
      ...canonical.map((p) => {
        const w = witnessByEntity.get(p.entity_id) ?? null;
        return {
          entityId: p.entity_id,
          canonical: p.value as number,
          witness: w && Math.abs(w.value - (p.value as number)) > 1e-9 ? w.value : null,
          witnessRoot: w?.root ?? null,
          witnessOnly: false,
        };
      }),
      ...witnessOnly,
    ];

    all.sort((a, b) => {
      const va = a.canonical ?? a.witness ?? Infinity;
      const vb = b.canonical ?? b.witness ?? Infinity;
      const cmp = higherIsBetter ? vb - va : va - vb;
      if (cmp !== 0) return cmp;
      return entityLabel(a.entityId, labelById.get(a.entityId)).localeCompare(
        entityLabel(b.entityId, labelById.get(b.entityId)),
      );
    });

    return all.map((r, i) => ({ ...r, rank: i + 1 }));
  }, [yearData, higherIsBetter, entityLabel, labelById]);

  /* ---------------- Focus row: bring into view (inner box only) ---------------- */
  const scrollBoxRef = useRef<HTMLDivElement>(null);
  const didScroll = useRef(false);

  useEffect(() => {
    if (!focusEntityId || rows.length === 0 || didScroll.current) return;
    const box = scrollBoxRef.current;
    const el = box?.querySelector<HTMLTableRowElement>(
      `[data-entity-id="${CSS.escape(focusEntityId)}"]`,
    );
    if (!box || !el) return;
    didScroll.current = true;
    const elTop = el.getBoundingClientRect().top;
    const boxTop = box.getBoundingClientRect().top;
    const boxH = box.clientHeight;
    // Scroll only the table container — never hijack the page scroll.
    if (elTop < boxTop || elTop > boxTop + boxH) {
      box.scrollTop += elTop - boxTop - boxH / 2;
    }
  }, [focusEntityId, rows.length]);

  useEffect(() => {
    // Re-arm the scroll when the focused country or indicator changes.
    didScroll.current = false;
  }, [focusEntityId, indicatorId]);

  const hasWitnessOnly = useMemo(() => rows.some((r) => r.witnessOnly), [rows]);

  return (
    <Card className={cn(fill && "xl:h-full")}>
      <CardHeader>
        <CardTitle className="font-serif-display text-lg">
          {t((d) => d.indicators.rankingTitle)}
        </CardTitle>
        <CardDescription>{unitLabel(unit)}</CardDescription>
        {year !== null && (
          <CardAction>
            <span className="text-xs text-muted-foreground tnum">
              {eventYear ? `≤ ${year}` : `${t((d) => d.common.year)} ${year}`}
              {sex !== "all" && (
                <>
                  {" · "}
                  {sex === "male" ? t((d) => d.common.male) : t((d) => d.common.female)}
                </>
              )}
            </span>
          </CardAction>
        )}
      </CardHeader>
      <CardContent className={cn(fill && "xl:min-h-0 xl:flex-1 xl:flex-col xl:flex")}>
        {isLoading ? (
          <SkeletonRows rows={8} />
        ) : rows.length === 0 ? (
          <EmptyBlock message={t((d) => d.common.noData)} />
        ) : (
          <>
            <div
              ref={scrollBoxRef}
              className={cn(
                "slim-scroll max-h-[28rem] overflow-y-auto rounded-md border",
                // xl: stop capping — the box then fills whatever height the
                // neighbouring series card gives the row.
                fill && "xl:min-h-0 xl:max-h-none xl:flex-1",
              )}
            >
              <Table>
                <TableHeader className="sticky top-0 z-10 bg-card [&>tr]:bg-card">
                  <TableRow className="hover:bg-transparent">
                    <TableHead className="w-12 text-right">#</TableHead>
                    <TableHead>{t((d) => d.common.country)}</TableHead>
                    <TableHead className="text-right">
                      {t((d) => d.common.value)}
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rows.map((row) => {
                    const displayValue = row.canonical ?? row.witness;
                    const isFocus = row.entityId === focusEntityId;
                    return (
                      <TableRow
                        key={row.entityId}
                        data-entity-id={row.entityId}
                        className={cn(
                          isFocus && "bg-primary/10 hover:bg-primary/15",
                        )}
                      >
                        <TableCell
                          className={cn(
                            "text-right tnum",
                            row.witnessOnly
                              ? "text-muted-foreground"
                              : "font-medium",
                          )}
                        >
                          {row.witnessOnly ? `${row.rank}*` : row.rank}
                        </TableCell>
                        <TableCell>
                          <Link
                            href={`/countries/${row.entityId}`}
                            className={cn(
                              "underline-offset-4 hover:underline",
                              row.witnessOnly
                                ? "text-muted-foreground"
                                : isFocus
                                  ? "font-semibold"
                                  : "",
                            )}
                          >
                            {entityLabel(row.entityId, labelById.get(row.entityId))}
                          </Link>
                        </TableCell>
                        <TableCell
                          className={cn(
                            "text-right tnum",
                            row.witnessOnly && "text-muted-foreground",
                          )}
                        >
                          {displayValue !== null && displayValue !== undefined
                            ? `${fmtNumber(displayValue, unit, lang)}${row.witnessOnly ? "*" : ""}`
                            : "-"}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
            {hasWitnessOnly && (
              <p className="mt-2 text-xs text-muted-foreground">
                {t((d) => d.indicators.rankingAsteriskNote)}
              </p>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
