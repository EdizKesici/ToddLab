"use client";

import { Check, ChevronsUpDown, Plus, X } from "lucide-react";
import * as React from "react";
import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { useCatalog, type CatalogItem } from "@/lib/toddlab/client";
import {
  useFamilyLabel,
  useI18n,
  useIndicatorLabel,
} from "@/lib/toddlab/i18n";
import { cn } from "@/lib/utils";
import { ToddCoreBadge } from "./badges";

export function MetricPicker({
  selected,
  onChange,
  max = 6,
  familyFilter,
  onFamilyFilterChange,
  className,
}: {
  selected: string[];
  onChange: (ids: string[]) => void;
  max?: number;
  familyFilter?: string | null;
  onFamilyFilterChange?: (f: string | null) => void;
  className?: string;
}) {
  const { t } = useI18n();
  const indicatorLabel = useIndicatorLabel();
  const familyLabel = useFamilyLabel();
  const { data } = useCatalog();
  const [open, setOpen] = React.useState(false);

  const indicators: CatalogItem[] = React.useMemo(() => {
    const list = (data?.indicators ?? []).filter((i) => i.available);
    return [...list].sort((a, b) =>
      indicatorLabel(a.id, a.label).localeCompare(indicatorLabel(b.id, b.label)),
    );
  }, [data, indicatorLabel]);

  const families = React.useMemo(() => {
    const set = new Set(indicators.map((i) => i.family));
    return [...set].sort();
  }, [indicators]);

  const toggle = (id: string) => {
    if (selected.includes(id)) {
      onChange(selected.filter((s) => s !== id));
    } else if (selected.length < max) {
      onChange([...selected, id]);
    }
  };

  return (
    <div className={cn("flex flex-wrap items-center gap-2", className)}>
      {selected.map((id) => {
        const ind = indicators.find((i) => i.id === id);
        return (
          <span
            key={id}
            className="inline-flex max-w-64 items-center gap-1.5 rounded-full border bg-card py-0.5 pl-2 pr-1 text-xs font-medium"
          >
            {ind?.todd_core && <ToddCoreBadge compact />}
            <span className="truncate">{indicatorLabel(id, ind?.label ?? id)}</span>
            <button
              onClick={() => toggle(id)}
              className="rounded-full p-0.5 hover:bg-accent transition-colors shrink-0"
              aria-label={`Remove ${indicatorLabel(id, ind?.label ?? id)}`}
            >
              <X className="h-3 w-3" />
            </button>
          </span>
        );
      })}
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            size="sm"
            role="combobox"
            aria-expanded={open}
            disabled={selected.length >= max}
            className="h-7 gap-1.5 rounded-full text-xs"
          >
            <Plus className="h-3 w-3" />
            {t((d) => d.compare.addMetric)}
            <span className="text-muted-foreground">
              {selected.length}/{max}
            </span>
            <ChevronsUpDown className="h-3 w-3 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-80 p-0" align="start">
          <Command>
            <CommandInput placeholder={t((d) => d.common.search)} />
            <CommandList className="slim-scroll max-h-96">
              <CommandEmpty>{t((d) => d.common.noData)}</CommandEmpty>
              <div className="border-b px-3 py-2">
                <div className="flex flex-wrap gap-1">
                  <button
                    onClick={() => onFamilyFilterChange?.(null)}
                    className={cn(
                      "rounded-full px-2 py-0.5 text-xs border transition-colors",
                      !familyFilter
                        ? "bg-primary text-primary-foreground border-primary"
                        : "hover:bg-accent",
                    )}
                  >
                    {t((d) => d.indicators.familyAll)}
                  </button>
                  {families.map((f) => (
                    <button
                      key={f}
                      onClick={() => onFamilyFilterChange?.(f)}
                      className={cn(
                        "rounded-full px-2 py-0.5 text-xs border transition-colors",
                        familyFilter === f
                          ? "bg-primary text-primary-foreground border-primary"
                          : "hover:bg-accent",
                      )}
                    >
                      {familyLabel(f)}
                    </button>
                  ))}
                </div>
              </div>
              <CommandGroup>
                {indicators
                  .filter((i) => !familyFilter || i.family === familyFilter)
                  .map((i) => {
                    const idx = selected.indexOf(i.id);
                    return (
                      <CommandItem
                        key={i.id}
                        value={`${indicatorLabel(i.id, i.label)} ${i.id}`}
                        onSelect={() => toggle(i.id)}
                        className="gap-2"
                      >
                        <Check
                          className={cn(
                            "h-4 w-4 shrink-0",
                            idx >= 0 ? "opacity-100" : "opacity-0",
                          )}
                        />
                        <span className="flex-1 truncate">
                          {indicatorLabel(i.id, i.label)}
                        </span>
                        {i.todd_core && <ToddCoreBadge compact />}
                      </CommandItem>
                    );
                  })}
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>
    </div>
  );
}
