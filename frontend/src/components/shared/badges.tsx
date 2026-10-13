"use client";

import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { ArrowDownRight, ArrowUpRight, BookOpen, ShieldCheck } from "lucide-react";
import { useI18n, useFamilyLabel } from "@/lib/toddlab/i18n";
import { cn } from "@/lib/utils";

export function ToddCoreBadge({ compact = false }: { compact?: boolean }) {
  const { t } = useI18n();
  return (
    <TooltipProvider delayDuration={200}>
      <Tooltip>
        <TooltipTrigger asChild>
          <Badge
            variant="outline"
            className="border-primary/40 bg-primary/5 text-primary gap-1"
          >
            <BookOpen className="h-3 w-3" />
            {compact ? "T" : t((d) => d.common.toddCore)}
          </Badge>
        </TooltipTrigger>
        <TooltipContent className="max-w-56 text-xs">
          {t((d) => d.common.toddCoreTip)}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

export function ReliabilityBadge({
  level,
  className,
}: {
  level: "high" | "medium" | "low";
  className?: string;
}) {
  const { t } = useI18n();
  const label =
    level === "high"
      ? t((d) => d.common.relHigh)
      : level === "medium"
        ? t((d) => d.common.relMedium)
        : t((d) => d.common.relLow);
  return (
    <Badge
      variant="secondary"
      className={cn(
        "gap-1 font-normal",
        level === "medium" && "bg-amber-500/10 text-amber-700 dark:text-amber-400",
        level === "low" && "bg-destructive/10 text-destructive",
        className,
      )}
    >
      <ShieldCheck className="h-3 w-3" />
      {label}
    </Badge>
  );
}

export function FamilyBadge({ family }: { family: string }) {
  const familyLabel = useFamilyLabel();
  return (
    <Badge variant="outline" className="font-normal text-muted-foreground">
      {familyLabel(family)}
    </Badge>
  );
}

export function DirectionBadge({ higherIsBetter }: { higherIsBetter: boolean }) {
  const { t } = useI18n();
  return (
    <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
      {higherIsBetter ? (
        <ArrowUpRight className="h-3.5 w-3.5 text-chart-8" />
      ) : (
        <ArrowDownRight className="h-3.5 w-3.5 text-primary" />
      )}
      {higherIsBetter
        ? t((d) => d.common.higherBetter)
        : t((d) => d.common.lowerBetter)}
    </span>
  );
}

export function WitnessTag({ label }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
      <span
        aria-hidden
        className="inline-block h-0 w-5 border-t-2 border-dashed border-witness"
      />
      {label ?? "Estimate"}
    </span>
  );
}
