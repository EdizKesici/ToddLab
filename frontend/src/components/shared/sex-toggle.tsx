"use client";

import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { useI18n } from "@/lib/toddlab/i18n";

export type SexChoice = "all" | "male" | "female";

export function SexToggle({
  value,
  onChange,
  className,
}: {
  value: SexChoice;
  onChange: (v: SexChoice) => void;
  className?: string;
}) {
  const { t } = useI18n();
  return (
    <ToggleGroup
      type="single"
      value={value}
      onValueChange={(v) => v && onChange(v as SexChoice)}
      className={className}
      aria-label="Sex"
    >
      <ToggleGroupItem value="all" size="sm" className="h-7 px-2.5 text-xs">
        {t((d) => d.common.bothSexes)}
      </ToggleGroupItem>
      <ToggleGroupItem value="male" size="sm" className="h-7 px-2.5 text-xs">
        {t((d) => d.common.male)}
      </ToggleGroupItem>
      <ToggleGroupItem value="female" size="sm" className="h-7 px-2.5 text-xs">
        {t((d) => d.common.female)}
      </ToggleGroupItem>
    </ToggleGroup>
  );
}
