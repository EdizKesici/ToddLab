"use client";

/**
 * Global search (command palette, Cmd/Ctrl+K).
 *
 * Fully client-side: the whole dataset's names (261 entities + ~27
 * indicators) is tiny, so there is nothing to index server-side — the labels
 * already arrive via React Query (entities + catalog) and are matched with a
 * diacritics-insensitive substring search. Selection navigates with the
 * router; the dialog closes on navigation.
 *
 * No hardcoded suggestions: with an empty query the palette shows a single
 * muted example hint — every listed entry comes from the actual search.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useCatalog, useEntities } from "@/lib/toddlab/client";
import {
  useEntityLabel,
  useI18n,
  useIndicatorLabel,
} from "@/lib/toddlab/i18n";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import { cn } from "@/lib/utils";

interface SearchItem {
  id: string;
  label: string;
  /** Extra match string (English label when browsing in French, raw id…). */
  alt: string;
  href: string;
  /** Small grey suffix, e.g. "ex-USSR" for successor states. */
  suffix?: string;
  keyword?: string;
}

/** Lowercase + strip diacritics so "fecondite" matches "Fécondité". */
function fold(s: string): string {
  return s
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

/** startsWith beats includes; both beat a plain id hit. */
function score(item: SearchItem, q: string): number {
  const label = fold(item.label);
  const alt = fold(item.alt);
  const keyword = fold(item.keyword ?? "");
  if (label.startsWith(q)) return 3;
  if (alt.startsWith(q)) return 2;
  if (label.includes(q) || alt.includes(q) || keyword.includes(q)) return 1;
  return 0;
}

export function GlobalSearch() {
  const { t, lang } = useI18n();
  const router = useRouter();
  const entityLabel = useEntityLabel();
  const indicatorLabel = useIndicatorLabel();

  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");

  const { data: entitiesData } = useEntities();
  const { data: catalogData } = useCatalog();

  // Cmd/Ctrl+K opens the palette (and "/" — standard site-search shortcut).
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((v) => !v);
      } else if (e.key === "/" && !open) {
        const target = e.target as HTMLElement | null;
        const typing =
          target &&
          (target.tagName === "INPUT" ||
            target.tagName === "TEXTAREA" ||
            target.isContentEditable);
        if (!typing) {
          e.preventDefault();
          setOpen(true);
        }
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  const closeAndGo = useCallback(
    (href: string) => {
      setOpen(false);
      setQuery("");
      router.push(href);
    },
    [router],
  );

  const pages = useMemo<SearchItem[]>(
    () => [
      { id: "compare", label: t((d) => d.nav.compare), alt: "comparer", href: "/compare" },
      { id: "countries", label: t((d) => d.nav.countries), alt: "pays pays", href: "/countries" },
      { id: "indicators", label: t((d) => d.nav.indicators), alt: "indicateurs", href: "/indicators" },
      { id: "methodology", label: t((d) => d.nav.methodology), alt: "methode", href: "/methodology" },
    ],
    [t],
  );

  const indicators = useMemo<SearchItem[]>(() => {
    return (catalogData?.indicators ?? []).map((i) => ({
      id: i.id,
      label: indicatorLabel(i.id, i.label),
      alt: i.label,
      href: `/indicators/${i.id}`,
      keyword: `${i.family} ${i.unit}`,
    }));
  }, [catalogData, indicatorLabel]);

  const countries = useMemo<SearchItem[]>(() => {
    return (entitiesData?.entities ?? []).map((e) => ({
      id: e.entity_id,
      label: entityLabel(e.entity_id, e.label),
      alt: e.label,
      href: `/countries/${e.entity_id}`,
      suffix: e.formerly_part_of
        ? e.formerly_part_of.union_entity_id === "ussr"
          ? "ex-USSR"
          : `ex-${e.formerly_part_of.union_entity_id.replace(/_/g, " ")}`
        : undefined,
    }));
  }, [entitiesData, entityLabel]);

  const hasQuery = fold(query.trim()).length > 0;

  const matches = useMemo(() => {
    const q = fold(query.trim());
    // Empty query: no suggestions at all — the user knows what to search for.
    if (!q) return { pages: [], indicators: [], countries: [] };
    const filter = (items: SearchItem[]) =>
      items
        .map((item) => ({ item, s: score(item, q) }))
        .filter((r) => r.s > 0)
        .sort((a, b) => b.s - a.s || a.item.label.localeCompare(b.item.label))
        .map((r) => r.item);
    return {
      pages: filter(pages).slice(0, 4),
      indicators: filter(indicators).slice(0, 12),
      countries: filter(countries).slice(0, 14),
    };
  }, [query, pages, indicators, countries]);

  const nothing =
    matches.pages.length === 0 &&
    matches.indicators.length === 0 &&
    matches.countries.length === 0;

  const run = (item: SearchItem) => closeAndGo(item.href);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label={t((d) => d.common.search)}
        aria-keyshortcuts="Meta+K Control+K"
        className={cn(
          "inline-flex h-9 items-center gap-2 rounded-md border border-input",
          "bg-transparent px-2.5 text-sm text-muted-foreground shadow-none",
          "transition-colors hover:bg-accent/60 hover:text-foreground",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        )}
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="size-4"
          aria-hidden
        >
          <circle cx="11" cy="11" r="8" />
          <path d="m21 21-4.3-4.3" />
        </svg>
        <span className="hidden lg:inline">
          {t((d) => d.common.searchAnything)}
        </span>
        <kbd className="pointer-events-none hidden lg:inline-flex h-5 select-none items-center gap-0.5 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground">
          {navigatorPlatformKey()}K
        </kbd>
      </button>

      <CommandDialog
        open={open}
        onOpenChange={(v) => {
          setOpen(v);
          if (!v) setQuery("");
        }}
        shouldFilter={false}
        title={t((d) => d.common.search)}
        description={t((d) => d.common.searchAnything)}
      >
        <CommandInput
          value={query}
          onValueChange={setQuery}
          placeholder={t((d) => d.common.searchAnything)}
        />
        <CommandList>
          {!hasQuery && (
            <div className="px-4 py-8 text-center text-sm text-muted-foreground">
              {t((d) => d.common.searchExample)}
            </div>
          )}
          {hasQuery && nothing && (
            <CommandEmpty>{t((d) => d.common.noResults)}</CommandEmpty>
          )}
          {matches.pages.length > 0 && (
            <CommandGroup heading={t((d) => d.common.groupPages)}>
              {matches.pages.map((item) => (
                <CommandItem
                  key={item.id}
                  value={`${item.label} ${item.alt}`}
                  onSelect={() => run(item)}
                >
                  <span>{item.label}</span>
                </CommandItem>
              ))}
            </CommandGroup>
          )}
          {matches.indicators.length > 0 && (
            <CommandGroup heading={t((d) => d.common.groupIndicators)}>
              {matches.indicators.map((item) => (
                <CommandItem
                  key={item.id}
                  value={`${item.label} ${item.alt} ${item.keyword ?? ""}`}
                  onSelect={() => run(item)}
                >
                  <div className="flex min-w-0 flex-col">
                    <span className="truncate">{item.label}</span>
                    {item.alt !== item.label && lang === "fr" && (
                      <span className="truncate text-xs text-muted-foreground">
                        {item.alt}
                      </span>
                    )}
                  </div>
                </CommandItem>
              ))}
            </CommandGroup>
          )}
          {matches.countries.length > 0 && (
            <CommandGroup heading={t((d) => d.common.groupCountries)}>
              {matches.countries.map((item) => (
                <CommandItem
                  key={item.id}
                  value={`${item.label} ${item.alt}`}
                  onSelect={() => run(item)}
                >
                  <div className="flex min-w-0 items-baseline gap-2">
                    <span className="truncate">{item.label}</span>
                    {item.suffix && (
                      <span className="shrink-0 text-xs text-muted-foreground">
                        {item.suffix}
                      </span>
                    )}
                  </div>
                </CommandItem>
              ))}
            </CommandGroup>
          )}
          {matches.pages.length > 0 &&
            (matches.indicators.length > 0 || matches.countries.length > 0) && (
              <CommandSeparator />
            )}
        </CommandList>
      </CommandDialog>
    </>
  );
}

/** "⌘" on Apple keyboards, "Ctrl" elsewhere — display only. */
function navigatorPlatformKey(): string {
  if (typeof window === "undefined") return "Ctrl+";
  return /mac|iphone|ipad/i.test(window.navigator.userAgent) ? "⌘" : "Ctrl+";
}
