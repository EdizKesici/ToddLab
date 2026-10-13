"use client";

import { Github } from "lucide-react";
import { useI18n } from "@/lib/toddlab/i18n";

export function SiteFooter() {
  const { t } = useI18n();
  return (
    <footer className="mt-auto border-t border-border/70 bg-secondary/40">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 pb-[max(2rem,env(safe-area-inset-bottom))]">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="max-w-md space-y-2">
            <p className="font-serif-display text-base font-semibold">
              Todd<span className="text-primary">Lab</span>
            </p>
            <p className="text-sm text-muted-foreground">
              {t((d) => d.home.footerBlurb)}
            </p>
          </div>
          <a
            href="https://github.com/EdizKesici/ToddLab"
            target="_blank"
            rel="noreferrer"
            className="inline-flex shrink-0 items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            <Github className="h-3.5 w-3.5" />
            {t((d) => d.common.github)}
          </a>
        </div>
      </div>
    </footer>
  );
}
