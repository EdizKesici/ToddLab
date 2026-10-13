"use client";

import { motion, type Variants } from "framer-motion";
import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { useI18n } from "@/lib/toddlab/i18n";

const container: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.07, delayChildren: 0.05 } },
};

const item: Variants = {
  hidden: { opacity: 0, y: 14 },
  show: { opacity: 1, y: 0, transition: { duration: 0.3, ease: "easeOut" } },
};

export function Hero() {
  const { t } = useI18n();

  return (
    <motion.section
      variants={container}
      initial="hidden"
      animate="show"
      className="py-16 sm:py-24"
      aria-labelledby="home-hero-title"
    >
      <motion.h1
        id="home-hero-title"
        variants={item}
        className="font-serif-display text-balance text-4xl font-semibold leading-[1.05] sm:text-6xl lg:text-7xl"
      >
        {t((d) => d.home.heroTitle)}
      </motion.h1>

      <motion.p
        variants={item}
        className="mt-6 max-w-3xl text-base leading-relaxed text-muted-foreground sm:text-lg"
      >
        {t((d) => d.home.heroDescription)}
      </motion.p>

      <motion.div variants={item} className="mt-9 flex flex-wrap items-center gap-3">
        <Button size="lg" asChild>
          <Link href="/compare">
            {t((d) => d.home.ctaCompare)}
            <ArrowRight />
          </Link>
        </Button>
        <Button size="lg" variant="outline" asChild>
          <Link href="/methodology">{t((d) => d.home.ctaMethod)}</Link>
        </Button>
      </motion.div>
    </motion.section>
  );
}
