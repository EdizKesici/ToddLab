"use client";

import { CircleCheck, CircleDot, CircleX, ExternalLink } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { interpolate, useI18n } from "@/lib/toddlab/i18n";
import type { PredictionsPayload, PredictionVerdict } from "@/lib/toddlab/types";
import { cn } from "@/lib/utils";

const TABLE_URL = "https://github.com/EdizKesici/ToddLab/blob/main/docs/todd_predictions.md";

const VERDICT_STYLE: Record<PredictionVerdict, { Icon: typeof CircleCheck; className: string }> = {
  verified: { Icon: CircleCheck, className: "text-emerald-600 dark:text-emerald-400" },
  partial: { Icon: CircleDot, className: "text-amber-600 dark:text-amber-400" },
  not_realized: { Icon: CircleX, className: "text-red-600 dark:text-red-400" },
};

export function PredictionsView({ data }: { data: PredictionsPayload }) {
  const { t, lang } = useI18n();

  const verdictLabel: Record<PredictionVerdict, string> = {
    verified: t((d) => d.predictions.verified),
    partial: t((d) => d.predictions.partial),
    not_realized: t((d) => d.predictions.notRealized),
  };

  return (
    <div className="mx-auto w-full max-w-4xl px-4 py-10 sm:px-6">
      <PageHeader
        title={t((d) => d.predictions.title)}
        subtitle={t((d) => d.predictions.subtitle)}
      />

      <div className="mb-10 space-y-3">
        <p className="text-sm text-muted-foreground">
          {interpolate(t((d) => d.predictions.count), {
            n: data.meta.n_predictions,
            b: data.meta.n_books,
          })}
        </p>
        <ul
          aria-label={t((d) => d.predictions.legendTitle)}
          className="flex w-fit flex-wrap items-center gap-x-6 gap-y-2 rounded-lg border bg-card px-4 py-3 text-sm"
        >
          {(Object.keys(VERDICT_STYLE) as PredictionVerdict[]).map((v) => {
            const { Icon, className } = VERDICT_STYLE[v];
            return (
              <li key={v} className="inline-flex items-center gap-2">
                <Icon aria-hidden className={cn("h-4 w-4", className)} />
                <span>{verdictLabel[v]}</span>
              </li>
            );
          })}
        </ul>
      </div>

      <div className="space-y-10">
        {data.books.map((book) => (
          <section key={book.label} aria-labelledby={`book-${book.label}`}>
            <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 border-b pb-2">
              <h2
                id={`book-${book.label}`}
                className="font-serif-display text-xl font-semibold tracking-tight sm:text-2xl"
              >
                {book.title}
              </h2>
              <span className="tnum text-sm text-muted-foreground">{book.year}</span>
              <span className="ml-auto text-xs text-muted-foreground">
                {book.predictions.length === 1
                  ? t((d) => d.predictions.bookPrediction)
                  : interpolate(t((d) => d.predictions.bookPredictions), { n: book.predictions.length })}
              </span>
            </div>
            <ul className="mt-3 space-y-2.5">
              {book.predictions.map((p, i) => {
                const { Icon, className } = VERDICT_STYLE[p.verdict];
                return (
                  <li key={i} className="flex items-start gap-3 text-[15px] leading-6">
                    <Icon
                      role="img"
                      aria-label={verdictLabel[p.verdict]}
                      className={cn("mt-0.5 h-4 w-4 shrink-0", className)}
                    >
                      <title>{verdictLabel[p.verdict]}</title>
                    </Icon>
                    <span>{lang === "fr" ? (p.text_fr ?? p.text) : p.text}</span>
                  </li>
                );
              })}
            </ul>
          </section>
        ))}
      </div>

      <div className="mt-12 max-w-3xl space-y-2 border-t pt-6 text-sm text-muted-foreground">
        <p>{t((d) => d.predictions.draftNote)}</p>
        <a
          href={TABLE_URL}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1.5 text-primary underline-offset-4 hover:underline"
        >
          {t((d) => d.predictions.fullTable)}
          <ExternalLink aria-hidden className="h-3.5 w-3.5" />
        </a>
      </div>
    </div>
  );
}
