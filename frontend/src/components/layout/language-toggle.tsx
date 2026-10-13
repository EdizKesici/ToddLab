"use client";

import { Languages } from "lucide-react";
import { useI18n } from "@/lib/toddlab/i18n";
import {
  ToggleGroup,
  ToggleGroupItem,
} from "@/components/ui/toggle-group";

export function LanguageToggle() {
  const { lang, setLang } = useI18n();
  return (
    <div className="flex items-center gap-1">
      <Languages className="h-3.5 w-3.5 text-muted-foreground" aria-hidden />
      <ToggleGroup
        type="single"
        value={lang}
        onValueChange={(v) => v && setLang(v as "en" | "fr")}
        aria-label="Language"
        className="gap-0.5"
      >
        <ToggleGroupItem
          value="en"
          aria-label="English"
          className="h-7 w-8 rounded-md px-1 text-xs font-medium data-[state=on]:bg-accent data-[state=on]:text-accent-foreground"
        >
          EN
        </ToggleGroupItem>
        <ToggleGroupItem
          value="fr"
          aria-label="Français"
          className="h-7 w-8 rounded-md px-1 text-xs font-medium data-[state=on]:bg-accent data-[state=on]:text-accent-foreground"
        >
          FR
        </ToggleGroupItem>
      </ToggleGroup>
    </div>
  );
}
