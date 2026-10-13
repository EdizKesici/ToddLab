"use client";

/**
 * URL-as-state for the /compare page.
 *
 * Shape: ?c=<countries>&m=<metrics>&mode=year|period&y=<year>&f=<from>&t=<to>&w=0|1&s=<metricId>:<all|male|female>,...
 * Absent params fall back to the defaults below. Updates replace the URL
 * (router.replace, scroll:false) — never push a history entry per interaction.
 */

import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useMemo } from "react";
import type { SexChoice } from "@/components/shared/sex-toggle";

export type CompareMode = "year" | "period";

export interface CompareQueryState {
  countries: string[];
  metrics: string[];
  mode: CompareMode;
  year: number;
  from: number;
  to: number;
  showWitness: boolean;
  /** Per-metric sex choice — only meaningful for sex_split metrics. */
  sexChoices: Record<string, SexChoice>;
}

export const COMPARE_DEFAULTS: Omit<CompareQueryState, "sexChoices"> = {
  countries: ["france", "united_states", "russian_federation"],
  metrics: ["infant_mortality", "life_expectancy"],
  mode: "year",
  year: 2020,
  from: 1970,
  to: 2024,
  showWitness: false,
};

export const MAX_COUNTRIES = 12;
export const MAX_METRICS = 6;

const SEX_VALUES: SexChoice[] = ["all", "male", "female"];

type ParamReader = Pick<URLSearchParams, "get">;

function parseList(raw: string | null, max: number): string[] | null {
  if (raw === null) return null;
  const parts = raw
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  if (parts.length === 0) return null;
  return [...new Set(parts)].slice(0, max);
}

function parseIntOrDefault(raw: string | null, fallback: number): number {
  if (raw === null) return fallback;
  const n = Number.parseInt(raw, 10);
  return Number.isFinite(n) ? n : fallback;
}

function parseSexChoices(raw: string | null): Record<string, SexChoice> {
  if (!raw) return {};
  const out: Record<string, SexChoice> = {};
  for (const part of raw.split(",")) {
    const [id, sex] = part.split(":");
    if (!id || !sex) continue;
    const normalized = sex.trim().toLowerCase();
    if ((SEX_VALUES as string[]).includes(normalized)) {
      out[id.trim()] = normalized as SexChoice;
    }
  }
  return out;
}

export function parseCompareState(sp: ParamReader): CompareQueryState {
  const mode = sp.get("mode");
  return {
    countries:
      parseList(sp.get("c"), MAX_COUNTRIES) ?? COMPARE_DEFAULTS.countries,
    metrics: parseList(sp.get("m"), MAX_METRICS) ?? COMPARE_DEFAULTS.metrics,
    mode: mode === "period" ? "period" : "year",
    year: parseIntOrDefault(sp.get("y"), COMPARE_DEFAULTS.year),
    from: parseIntOrDefault(sp.get("f"), COMPARE_DEFAULTS.from),
    to: parseIntOrDefault(sp.get("t"), COMPARE_DEFAULTS.to),
    showWitness: sp.get("w") === "1",
    sexChoices: parseSexChoices(sp.get("s")),
  };
}

export function serializeCompareState(s: CompareQueryState): string {
  const sp = new URLSearchParams();
  if (s.countries.length > 0) sp.set("c", s.countries.join(","));
  if (s.metrics.length > 0) sp.set("m", s.metrics.join(","));
  sp.set("mode", s.mode);
  sp.set("y", String(s.year));
  sp.set("f", String(s.from));
  sp.set("t", String(s.to));
  sp.set("w", s.showWitness ? "1" : "0");
  const sex = Object.entries(s.sexChoices)
    .filter(([, v]) => v !== "all")
    .map(([k, v]) => `${k}:${v}`)
    .join(",");
  if (sex) sp.set("s", sex);
  return sp.toString();
}

export function useCompareQueryState(): {
  state: CompareQueryState;
  patch: (partial: Partial<CompareQueryState>) => void;
} {
  const router = useRouter();
  const sp = useSearchParams();

  const state = useMemo(() => parseCompareState(sp), [sp]);

  const patch = useCallback(
    (partial: Partial<CompareQueryState>) => {
      // Merge from the live URL (not the render-time snapshot) so rapid
      // successive interactions on different controls never lose updates.
      const current = parseCompareState(
        new URLSearchParams(window.location.search),
      );
      const next: CompareQueryState = { ...current, ...partial };
      router.replace(`/compare?${serializeCompareState(next)}`, {
        scroll: false,
      });
    },
    [router],
  );

  return { state, patch };
}
