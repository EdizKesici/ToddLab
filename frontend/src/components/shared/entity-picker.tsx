"use client";

import { Check, ChevronsUpDown, Search, X } from "lucide-react";
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
import { useEntities, type EntityItem } from "@/lib/toddlab/client";
import { useEntityLabel, useI18n } from "@/lib/toddlab/i18n";
import { cn } from "@/lib/utils";

export const COUNTRY_COLORS = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
  "var(--chart-6)",
  "var(--chart-7)",
  "var(--chart-8)",
  "var(--chart-9)",
  "var(--chart-10)",
  "var(--chart-11)",
  "var(--chart-12)",
];

export function colorForIndex(i: number): string {
  return COUNTRY_COLORS[i % COUNTRY_COLORS.length];
}

export function EntityPicker({
  selected,
  onChange,
  max = 8,
  className,
}: {
  selected: string[];
  onChange: (ids: string[]) => void;
  max?: number;
  className?: string;
}) {
  const { t } = useI18n();
  const entityLabel = useEntityLabel();
  const { data } = useEntities();
  const [open, setOpen] = React.useState(false);
  const entities: EntityItem[] = React.useMemo(() => {
    const list = data?.entities ?? [];
    return [...list].sort((a, b) =>
      entityLabel(a.entity_id, a.label).localeCompare(
        entityLabel(b.entity_id, b.label),
      ),
    );
  }, [data, entityLabel]);

  const toggle = (id: string) => {
    if (selected.includes(id)) {
      onChange(selected.filter((s) => s !== id));
    } else if (selected.length < max) {
      onChange([...selected, id]);
    }
  };

  return (
    <div className={cn("flex flex-wrap items-center gap-2", className)}>
      {selected.map((id, i) => {
        const ent = entities.find((e) => e.entity_id === id);
        return (
          <span
            key={id}
            className="inline-flex items-center gap-1.5 rounded-full border bg-card py-0.5 pl-2 pr-1 text-xs font-medium"
          >
            <span
              aria-hidden
              className="h-2 w-2 rounded-full"
              style={{ background: colorForIndex(i) }}
            />
            {entityLabel(id, ent?.label)}
            <button
              onClick={() => toggle(id)}
              className="rounded-full p-0.5 hover:bg-accent transition-colors"
              aria-label={`Remove ${entityLabel(id, ent?.label)}`}
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
            <Search className="h-3 w-3" />
            {t((d) => d.compare.addCountry)}
            <span className="text-muted-foreground">
              {selected.length}/{max}
            </span>
            <ChevronsUpDown className="h-3 w-3 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-72 p-0" align="start">
          <Command>
            <CommandInput placeholder={t((d) => d.common.search)} />
            <CommandList className="slim-scroll max-h-72">
              <CommandEmpty>{t((d) => d.common.noData)}</CommandEmpty>
              <CommandGroup>
                {entities.map((e) => {
                  const idx = selected.indexOf(e.entity_id);
                  return (
                    <CommandItem
                      key={e.entity_id}
                      value={`${entityLabel(e.entity_id, e.label)} ${e.entity_id} ${e.iso3 ?? ""}`}
                      onSelect={() => toggle(e.entity_id)}
                      className="gap-2"
                    >
                      <Check
                        className={cn(
                          "h-4 w-4",
                          idx >= 0 ? "opacity-100" : "opacity-0",
                        )}
                      />
                      <span className="flex-1 truncate">
                        {entityLabel(e.entity_id, e.label)}
                      </span>
                      {e.iso3 && (
                        <span className="text-xs text-muted-foreground tnum">
                          {e.iso3}
                        </span>
                      )}
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
