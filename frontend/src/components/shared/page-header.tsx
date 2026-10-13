"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export function PageHeader({
  title,
  subtitle,
  subtitleClassName,
  children,
  className,
}: {
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  subtitleClassName?: string;
  children?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("mb-8 space-y-3", className)}>
      <div className="space-y-2">
        <h1 className="font-serif-display text-3xl sm:text-4xl font-semibold tracking-tight text-balance">
          {title}
        </h1>
        {subtitle && (
          <p
            className={cn(
              "max-w-3xl text-sm sm:text-base text-muted-foreground text-balance",
              subtitleClassName,
            )}
          >
            {subtitle}
          </p>
        )}
      </div>
      {children}
    </div>
  );
}

export function SectionTitle({
  children,
  className,
  hint,
}: {
  children: React.ReactNode;
  className?: string;
  hint?: React.ReactNode;
}) {
  return (
    <div className={cn("mb-4", className)}>
      <h2 className="font-serif-display text-xl font-semibold tracking-tight">
        {children}
      </h2>
      {hint && <p className="mt-1 text-sm text-muted-foreground">{hint}</p>}
    </div>
  );
}
