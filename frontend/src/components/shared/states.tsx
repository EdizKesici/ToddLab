"use client";

import { AlertTriangle, Inbox, Loader2 } from "lucide-react";
import * as React from "react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useI18n } from "@/lib/toddlab/i18n";
import { cn } from "@/lib/utils";

export function LoadingBlock({ className, label }: { className?: string; label?: string }) {
  return (
    <div
      className={cn(
        "flex min-h-40 flex-col items-center justify-center gap-3 text-sm text-muted-foreground",
        className,
      )}
      role="status"
      aria-live="polite"
    >
      <Loader2 className="h-6 w-6 animate-spin text-primary" />
      {label ?? "Loading…"}
    </div>
  );
}

export function SkeletonRows({ rows = 5, className }: { rows?: number; className?: string }) {
  return (
    <div className={cn("space-y-2", className)}>
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-8 w-full" />
      ))}
    </div>
  );
}

export function ErrorBlock({
  onRetry,
  className,
}: {
  onRetry?: () => void;
  className?: string;
}) {
  const { t } = useI18n();
  return (
    <div
      className={cn(
        "flex min-h-40 flex-col items-center justify-center gap-3 text-sm text-muted-foreground",
        className,
      )}
      role="alert"
    >
      <AlertTriangle className="h-6 w-6 text-destructive" />
      {t((d) => d.common.error)}
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry}>
          {t((d) => d.common.retry)}
        </Button>
      )}
    </div>
  );
}

export function EmptyBlock({
  message,
  className,
  icon,
}: {
  message: string;
  className?: string;
  icon?: React.ReactNode;
}) {
  return (
    <div
      className={cn(
        "flex min-h-40 flex-col items-center justify-center gap-3 text-sm text-muted-foreground",
        className,
      )}
    >
      {icon ?? <Inbox className="h-6 w-6" />}
      {message}
    </div>
  );
}
