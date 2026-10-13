"use client";

import { motion } from "framer-motion";
import { ArrowRight, Sparkles } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useEntityLabel, useI18n } from "@/lib/toddlab/i18n";
import { useEntities, useScoreRankings } from "@/lib/toddlab/client";
import { fmtScore } from "@/lib/toddlab/format";

const TOP_N = 5;

function TopList({
  rows,
  onLabel,
  limit = TOP_N,
}: {
  rows: { entity_id: string; score: number }[];
  onLabel: (id: string) => string;
  limit?: number;
}) {
  return (
    <ol className="space-y-1.5">
      {rows.slice(0, limit).map((r, i) => (
        <li key={r.entity_id} className="flex items-center gap-2.5 text-sm">
          <span className="tnum w-5 shrink-0 text-right text-xs text-muted-foreground">
            {i + 1}
          </span>
          <Link
            href={`/countries/${r.entity_id}`}
            className="min-w-0 flex-1 truncate underline-offset-4 hover:text-primary hover:underline"
          >
            {onLabel(r.entity_id)}
          </Link>
          <span className="tnum shrink-0 font-semibold">{fmtScore(r.score)}</span>
        </li>
      ))}
    </ol>
  );
}

export function ScoreTeaser() {
  const { t, lang } = useI18n();
  const entityLabel = useEntityLabel();
  const entities = useEntities();
  const rankings = useScoreRankings(null);

  const labelOf = (id: string) =>
    entityLabel(id, entities.data?.entities.find((e) => e.entity_id === id)?.label);

  const data = rankings.data;
  const officialTop = data?.rankings.official.equal ?? [];
  const modelledTop = data?.rankings.modelled.equal ?? [];
  const year = data && data.year !== 0 ? data.year : null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-40px" }}
      transition={{ duration: 0.25, ease: "easeOut" }}
      className="rounded-xl border bg-card p-6 sm:p-8"
    >
      <div className="flex flex-col gap-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:gap-6">
          <span
            aria-hidden
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary"
          >
            <Sparkles className="h-5 w-5" />
          </span>
          <div className="space-y-2.5">
            <div className="flex flex-wrap items-center gap-3">
              <h3 className="font-serif-display text-xl font-semibold tracking-tight">
                {t((d) => d.home.scoreTitle)}
              </h3>
            </div>
            <p className="max-w-3xl text-sm leading-relaxed text-muted-foreground">
              {t((d) => d.home.scoreText)}
            </p>
          </div>
        </div>

        {rankings.isError ? null : !data ? (
          <div className="grid gap-6 sm:grid-cols-2">
            {[0, 1].map((i) => (
              <div key={i} className="space-y-2.5">
                <Skeleton className="h-4 w-40" />
                {Array.from({ length: TOP_N }).map((_, j) => (
                  <Skeleton key={j} className="h-5 w-full" />
                ))}
              </div>
            ))}
          </div>
        ) : (
          <div className="grid gap-6 sm:grid-cols-2">
            <div className="rounded-lg border bg-background/60 p-4">
              <div className="mb-3 flex items-center justify-between">
                <h4 className="text-sm font-semibold">
                  {t((d) => d.score.official)}
                  {year !== null && <span className="tnum ml-1.5 font-normal text-muted-foreground">· {year}</span>}
                </h4>
                <Link
                  href="/score?s=official&p=equal"
                  className="text-xs text-muted-foreground underline-offset-4 hover:text-primary hover:underline"
                >
                  {t((d) => d.score.ctaRankings)}
                </Link>
              </div>
              <TopList rows={officialTop} onLabel={labelOf} />
            </div>
            <div className="rounded-lg border bg-background/60 p-4">
              <div className="mb-3 flex items-center justify-between">
                <h4 className="text-sm font-semibold">
                  {t((d) => d.score.modelled)}
                  {year !== null && <span className="tnum ml-1.5 font-normal text-muted-foreground">· {year}</span>}
                </h4>
                <Link
                  href="/score?s=modelled&p=equal"
                  className="text-xs text-muted-foreground underline-offset-4 hover:text-primary hover:underline"
                >
                  {t((d) => d.score.ctaRankings)}
                </Link>
              </div>
              <TopList rows={modelledTop} onLabel={labelOf} />
            </div>
          </div>
        )}

        <div>
          <Button asChild size="sm" className="gap-1.5">
            <Link href="/score">
              {t((d) => d.home.scoreCta)}
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </Button>
        </div>

        <p className="sr-only">
          {lang === "fr"
            ? "Classement des scores civilisationnels, officiel et modélisé."
            : "Civilizational score rankings, official and modelled."}
        </p>
      </div>
    </motion.div>
  );
}
