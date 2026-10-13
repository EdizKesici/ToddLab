"use client";

import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { useCatalog } from "@/lib/toddlab/client";
import { useI18n, type Lang } from "@/lib/toddlab/i18n";

interface StatDef {
  target: number | null;
  label: string;
  suffix?: string;
  compact?: boolean;
}

function formatStat(value: number, lang: Lang, compact: boolean): string {
  const locale = lang === "fr" ? "fr-FR" : "en-US";
  if (compact) {
    return new Intl.NumberFormat(locale, {
      notation: "compact",
      maximumFractionDigits: 1,
    }).format(value);
  }
  return new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(value);
}

function StatItem({
  stat,
  index,
  lang,
}: {
  stat: StatDef;
  index: number;
  lang: Lang;
}) {
  const [started, setStarted] = useState(false);
  const [display, setDisplay] = useState<number | null>(null);

  const startCount = useCallback(() => setStarted(true), []);

  useEffect(() => {
    if (!started || stat.target === null) return;
    const target = stat.target;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const duration = reduce ? 0 : 1100;
    let raf = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const p = duration === 0 ? 1 : Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - p, 3);
      setDisplay(target * eased);
      if (p < 1) {
        raf = requestAnimationFrame(tick);
      } else {
        setDisplay(target);
      }
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [started, stat.target]);

  const text =
    display === null ? "…" : formatStat(display, lang, stat.compact ?? false);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-40px" }}
      transition={{ duration: 0.25, delay: index * 0.04, ease: "easeOut" }}
      onViewportEnter={startCount}
      className="flex flex-col"
    >
      <dt className="order-2 mt-1.5 text-xs leading-snug text-muted-foreground">
        {stat.label}
      </dt>
      <dd className="tnum order-1 text-2xl font-semibold tracking-tight sm:text-3xl">
        {text}
        {stat.suffix && display !== null && (
          <span className="text-primary">{stat.suffix}</span>
        )}
      </dd>
    </motion.div>
  );
}

export function StatsBand() {
  const { t, lang } = useI18n();
  const { data } = useCatalog();
  const meta = data?.meta;

  const stats: StatDef[] = [
    {
      target: meta?.n_indicators_available ?? null,
      label: t((d) => d.home.statsIndicators),
    },
    {
      target: meta?.n_entities ?? null,
      label: t((d) => d.home.statsCountries),
    },
    {
      target: meta?.n_canonical_points ?? null,
      label: t((d) => d.home.statsCanonical),
      compact: true,
    },
    {
      target: meta?.n_witness_points ?? null,
      label: t((d) => d.home.statsWitness),
      compact: true,
    },
    {
      target: meta?.corpus.books ?? null,
      label: t((d) => d.home.statsBooks),
    },
  ];

  return (
    <section className="border-y border-border/60 bg-secondary/40">
      <div className="mx-auto w-full max-w-6xl px-4 py-12 sm:px-6 sm:py-14 lg:px-8">
        <dl className="grid grid-cols-2 gap-x-6 gap-y-8 sm:grid-cols-3 lg:grid-cols-5">
          {stats.map((stat, i) => (
            <StatItem key={i} stat={stat} index={i} lang={lang} />
          ))}
        </dl>
      </div>
    </section>
  );
}
