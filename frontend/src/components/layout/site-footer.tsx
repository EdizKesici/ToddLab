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
          <div className="flex shrink-0 flex-wrap items-center gap-x-5 gap-y-2 text-sm text-muted-foreground">
            <a
              href="https://github.com/EdizKesici/ToddLab"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 transition-colors hover:text-foreground"
            >
              <Github className="h-3.5 w-3.5" />
              {t((d) => d.common.github)}
            </a>
            <a
              href="https://github.com/EdizKesici/ToddLab/blob/main/LICENSE"
              target="_blank"
              rel="noreferrer"
              className="transition-colors hover:text-foreground"
            >
              {t((d) => d.common.license)}
            </a>
            <a
              href="https://github.com/EdizKesici/ToddLab/blob/main/docs/licenses.md"
              target="_blank"
              rel="noreferrer"
              className="transition-colors hover:text-foreground"
            >
              {t((d) => d.common.dataCredits)}
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
