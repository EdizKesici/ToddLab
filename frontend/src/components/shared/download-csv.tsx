"use client";

import { Download } from "lucide-react";
import { useI18n } from "@/lib/toddlab/i18n";
import { cn } from "@/lib/utils";

/** Plain link to a CSV route: the browser downloads it (Content-Disposition: attachment). */
export function DownloadCsv({ href, className }: { href: string; className?: string }) {
  const { t } = useI18n();
  return (
    <a
      href={href}
      download
      className={cn(
        "inline-flex w-fit items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-medium text-foreground transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        className,
      )}
    >
      <Download className="h-3.5 w-3.5 text-primary" aria-hidden />
      {t((d) => d.common.downloadCsv)}
    </a>
  );
}
