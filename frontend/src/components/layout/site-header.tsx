"use client";

import { Activity } from "lucide-react";
import { usePathname } from "next/navigation";
import Link from "next/link";
import { useI18n } from "@/lib/toddlab/i18n";
import { GlobalSearch } from "./global-search";
import { LanguageToggle } from "./language-toggle";
import { ThemeToggle } from "./theme-toggle";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/", key: "home" },
  { href: "/compare", key: "compare" },
  { href: "/countries", key: "countries" },
  { href: "/indicators", key: "indicators" },
  { href: "/score", key: "score" },
  { href: "/predictions", key: "predictions" },
  { href: "/methodology", key: "methodology" },
] as const;

export function SiteHeader() {
  const { t } = useI18n();
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/70 bg-background/80 backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-7xl items-center gap-4 px-4 sm:px-6">
        <Link href="/" className="flex items-center gap-2 shrink-0 group">
          <span className="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-primary-foreground transition-transform group-hover:scale-105">
            <Activity className="h-4 w-4" strokeWidth={2.5} />
          </span>
          <span className="font-serif-display text-lg font-semibold tracking-tight">
            Todd<span className="text-primary">Lab</span>
          </span>
        </Link>

        <nav aria-label="Main" className="hidden md:flex items-center gap-1">
          {NAV.map((item) => {
            const active =
              item.href === "/"
                ? pathname === "/"
                : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "rounded-md px-3 py-1.5 text-sm transition-colors",
                  active
                    ? "bg-accent text-accent-foreground font-medium"
                    : "text-muted-foreground hover:text-foreground hover:bg-accent/60",
                )}
              >
                {t((d) => d.nav[item.key as keyof typeof d.nav] as string)}
              </Link>
            );
          })}
        </nav>

        <div className="ml-auto flex items-center gap-1.5">
          <GlobalSearch />
          <LanguageToggle />
          <ThemeToggle />
        </div>
      </div>

      {/* Mobile nav */}
      <nav
        aria-label="Mobile"
        className="md:hidden flex items-center gap-1 overflow-x-auto px-3 pb-2 slim-scroll"
      >
        {NAV.map((item) => {
          const active =
            item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "whitespace-nowrap rounded-md px-3 py-1.5 text-sm transition-colors",
                active
                  ? "bg-accent text-accent-foreground font-medium"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {t((d) => d.nav[item.key as keyof typeof d.nav] as string)}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
