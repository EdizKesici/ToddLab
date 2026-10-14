"use client";

import { motion } from "framer-motion";
import {
  ArrowUpRight,
  BarChart3,
  GitCompareArrows,
  Globe2,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { useCatalog } from "@/lib/toddlab/client";
import { interpolate, useI18n } from "@/lib/toddlab/i18n";

interface Teaser {
  href: string;
  icon: LucideIcon;
  title: string;
  text: string;
}

export function TeaserCards() {
  const { t } = useI18n();
  const { data } = useCatalog();
  const nIndicators = data ? data.meta.n_indicators_available : "…";

  const teasers: Teaser[] = [
    {
      href: "/compare",
      icon: GitCompareArrows,
      title: t((d) => d.home.compareTeaserTitle),
      text: t((d) => d.home.compareTeaserText),
    },
    {
      href: "/countries",
      icon: Globe2,
      title: t((d) => d.home.countryTeaserTitle),
      text: t((d) => d.home.countryTeaserText),
    },
    {
      href: "/indicators",
      icon: BarChart3,
      title: t((d) => d.home.indicatorTeaserTitle),
      text: interpolate(t((d) => d.home.indicatorTeaserText), { n: nIndicators }),
    },
  ];

  return (
    <section>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {teasers.map((teaser, i) => {
          const Icon = teaser.icon;
          return (
            <motion.div
              key={teaser.href}
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-40px" }}
              transition={{ duration: 0.25, delay: i * 0.05, ease: "easeOut" }}
              whileHover={{ y: -4 }}
              className="h-full"
            >
              <Link
                href={teaser.href}
                className="group flex h-full flex-col gap-3 rounded-xl border bg-card p-6 shadow-xs transition-colors hover:border-primary/40 hover:bg-accent/40 focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
              >
                <div className="flex items-center justify-between">
                  <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <Icon className="h-5 w-5" aria-hidden />
                  </span>
                  <ArrowUpRight
                    aria-hidden
                    className="h-4 w-4 text-muted-foreground/40 transition-all duration-200 group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-primary"
                  />
                </div>
                <h3 className="font-serif-display text-lg font-semibold tracking-tight">
                  {teaser.title}
                </h3>
                <p className="text-sm leading-relaxed text-muted-foreground">
                  {teaser.text}
                </p>
              </Link>
            </motion.div>
          );
        })}
      </div>
    </section>
  );
}
