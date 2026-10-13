"use client";

import { motion } from "framer-motion";
import { ArrowRight, Github, Sparkles } from "lucide-react";
import Link from "next/link";
import { WitnessTag } from "@/components/shared/badges";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useCatalog } from "@/lib/toddlab/client";
import { interpolate, useI18n } from "@/lib/toddlab/i18n";
import { FoundingCaseChart } from "./founding-case-chart";

function BodyText({ children }: { children: React.ReactNode }) {
  return <p className="text-[15px] leading-7 text-foreground/85">{children}</p>;
}

function NumberedSection({
  index,
  title,
  children,
}: {
  index: number;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-60px" }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      aria-labelledby={`method-s${index}`}
      className="py-10 first:pt-2 last:pb-0 sm:py-12"
    >
      <div className="flex items-baseline gap-3 sm:gap-4">
        <span
          aria-hidden
          className="tnum font-serif-display text-xl font-semibold text-primary/60 sm:text-2xl"
        >
          {String(index).padStart(2, "0")}
        </span>
        <h2
          id={`method-s${index}`}
          className="font-serif-display text-xl font-semibold tracking-tight sm:text-2xl"
        >
          {title}
        </h2>
      </div>
      <div className="mt-4 max-w-3xl space-y-5 sm:pl-12">{children}</div>
    </motion.section>
  );
}

/** Mini-legend for the two tiers: solid terracotta = canonical, dashed gray = witness. */
function SeriesLegend() {
  const { t } = useI18n();
  return (
    <div className="flex w-fit flex-wrap items-center gap-x-8 gap-y-3 rounded-lg border bg-card px-4 py-3">
      <span className="inline-flex items-center gap-2 text-sm">
        <span
          aria-hidden
          className="inline-block h-0.5 w-8 rounded-full"
          style={{ background: "var(--chart-1)" }}
        />
        <span className="font-medium">{t((d) => d.common.canonical)}</span>
      </span>
      <WitnessTag label={t((d) => d.common.witness)} />
    </div>
  );
}

export function MethodView() {
  const { t, lang } = useI18n();
  const { data: catalog } = useCatalog();
  const meta = catalog?.meta;
  const locale = lang === "fr" ? "fr-FR" : "en-US";

  const s6Body = interpolate(t((d) => d.method.s6Body), {
    indicators: meta ? meta.n_indicators_available : "…",
    entities: meta ? meta.n_entities : "…",
    canonical: meta ? meta.n_canonical_points.toLocaleString(locale) : "…",
    witness: meta ? meta.n_witness_points.toLocaleString(locale) : "…",
  });

  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-12 sm:px-6 sm:py-16 lg:px-8">
      <PageHeader
        title={t((d) => d.method.title)}
        subtitle={t((d) => d.method.subtitle)}
      />

      <div className="divide-y divide-border/70 border-t border-border/70">
        <NumberedSection index={1} title={t((d) => d.method.s1Title)}>
          <BodyText>{t((d) => d.method.s1Body)}</BodyText>
        </NumberedSection>

        <NumberedSection index={2} title={t((d) => d.method.s2Title)}>
          <BodyText>{t((d) => d.method.s2Body)}</BodyText>
          <SeriesLegend />
        </NumberedSection>

        <NumberedSection index={3} title={t((d) => d.method.s3Title)}>
          <BodyText>{t((d) => d.method.s3Body)}</BodyText>
        </NumberedSection>

        <NumberedSection index={4} title={t((d) => d.method.s4Title)}>
          <BodyText>{t((d) => d.method.s4Body)}</BodyText>
          <FoundingCaseChart />
        </NumberedSection>

        <NumberedSection index={5} title={t((d) => d.method.s5Title)}>
          <BodyText>{t((d) => d.method.s5Body)}</BodyText>
        </NumberedSection>

        <NumberedSection index={6} title={t((d) => d.method.s6Title)}>
          <BodyText>{s6Body}</BodyText>
        </NumberedSection>
      </div>

      <div className="mt-14 space-y-10 sm:mt-16">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-40px" }}
          transition={{ duration: 0.25, ease: "easeOut" }}
        >
          <Card>
            <CardHeader>
              <CardTitle className="flex flex-wrap items-center gap-x-3 gap-y-2 font-serif-display text-lg sm:text-xl">
                <span
                  aria-hidden
                  className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary"
                >
                  <Sparkles className="h-4 w-4" />
                </span>
                {t((d) => d.method.scoreComingTitle)}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="max-w-3xl text-sm leading-relaxed text-muted-foreground">
                {t((d) => d.method.scoreComingBody)}
              </p>
              <Button asChild size="sm" className="mt-4 gap-1.5">
                <Link href="/score">
                  {t((d) => d.home.scoreCta)}
                  <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              </Button>
            </CardContent>
          </Card>
        </motion.div>

        <div>
          <Button variant="outline" asChild>
            <a
              href="https://github.com/EdizKesici/ToddLab"
              target="_blank"
              rel="noopener noreferrer"
            >
              <Github />
              {t((d) => d.common.github)}
            </a>
          </Button>
        </div>
      </div>
    </div>
  );
}
