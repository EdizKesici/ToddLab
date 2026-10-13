"use client";

/**
 * URL-as-state for /indicators/[id].
 *
 * Shape: ?country=<focus>&y=<year>&s=<all|male|female>&c=<series,countries>&sp=<series sex>&w=0|1
 * - country : focused country (arrival from a country profile) — carried through untouched
 * - y       : reference year for the map + ranking (omitted when it equals the default)
 * - s       : sex for the map + ranking (omitted when "all")
 * - c       : countries shown in the time-series card (omitted when equal to the initial selection)
 * - sp      : sex of the series card (omitted when "all")
 * - w       : witness/estimates toggle of the series card (omitted when off)
 * - b       : base-100 index of the series card (omitted when off)
 *
 * Absent params always fall back to the same deterministic defaults, so a URL
 * without params reproduces the default view exactly. Updates replace the URL
 * (router.replace, scroll:false) — never push a history entry per interaction.
 */

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef } from "react";
import type { SexChoice } from "@/components/shared/sex-toggle";

export const SERIES_MAX_COUNTRIES = 6;

export interface IndicatorQueryState {
  /** ?country= — focused entity, passed through untouched. */
  country: string | null;
  /** ?y= — explicit reference year; null = default logic applies. */
  year: number | null;
  /** ?s= — sex for map + ranking. */
  sex: SexChoice;
  /** ?c= — series countries; null = initial selection applies. */
  seriesCountries: string[] | null;
  /** ?sp= — series card sex. */
  seriesSex: SexChoice;
  /** ?w=1 — series card estimates toggle. */
  witness: boolean;
  /** ?b=1 — series card base-100 index. */
  base100: boolean;
}

export interface IndicatorQueryDefaults {
  /** The year a URL without ?y= resolves to — omitted from serialized URLs. */
  defaultYear: number | null;
  /** The countries a URL without ?c= resolves to — omitted from serialized URLs. */
  initialCountries: string[];
}

const SEX_VALUES: SexChoice[] = ["all", "male", "female"];

type ParamReader = Pick<URLSearchParams, "get">;

function parseSex(raw: string | null): SexChoice {
  return (SEX_VALUES as string[]).includes(raw ?? "") ? (raw as SexChoice) : "all";
}

function parseCountries(raw: string | null): string[] | null {
  if (raw === null) return null;
  const parts = raw
    .split(",")
    .map((s) => s.trim())
    .filter((s) => /^[a-z][a-z0-9_]*$/.test(s));
  if (parts.length === 0) return null;
  return [...new Set(parts)].slice(0, SERIES_MAX_COUNTRIES);
}

function parseState(sp: ParamReader): IndicatorQueryState {
  const focus = sp.get("country");
  const yRaw = sp.get("y");
  const year = yRaw === null ? Number.NaN : Number.parseInt(yRaw, 10);
  return {
    country: focus && focus.trim() !== "" ? focus.trim() : null,
    year: Number.isFinite(year) ? year : null,
    sex: parseSex(sp.get("s")),
    seriesCountries: parseCountries(sp.get("c")),
    seriesSex: parseSex(sp.get("sp")),
    witness: sp.get("w") === "1",
    base100: sp.get("b") === "1",
  };
}

function serialize(
  state: IndicatorQueryState,
  defaults: IndicatorQueryDefaults,
): string {
  const sp = new URLSearchParams();
  if (state.country) sp.set("country", state.country);
  if (state.year !== null && state.year !== defaults.defaultYear) {
    sp.set("y", String(state.year));
  }
  if (state.sex !== "all") sp.set("s", state.sex);
  if (
    state.seriesCountries &&
    state.seriesCountries.length > 0 &&
    state.seriesCountries.join(",") !== defaults.initialCountries.join(",")
  ) {
    sp.set("c", state.seriesCountries.join(","));
  }
  if (state.seriesSex !== "all") sp.set("sp", state.seriesSex);
  if (state.witness) sp.set("w", "1");
  if (state.base100) sp.set("b", "1");
  return sp.toString();
}

export function useIndicatorQueryState(defaults: IndicatorQueryDefaults): {
  state: IndicatorQueryState;
  patch: (partial: Partial<Omit<IndicatorQueryState, "country">>) => void;
} {
  const router = useRouter();
  const pathname = usePathname();
  const sp = useSearchParams();

  const state = useMemo(() => parseState(sp), [sp]);

  // Keep the latest defaults in a ref so `patch` stays referentially stable
  // while the page renders (defaults derive from async metadata).
  const defaultsRef = useRef(defaults);
  useEffect(() => {
    defaultsRef.current = defaults;
  }, [defaults]);

  const patch = useCallback(
    (partial: Partial<Omit<IndicatorQueryState, "country">>) => {
      // Merge from the live URL (not the render-time snapshot) so rapid
      // successive interactions on different controls never lose updates.
      const current = parseState(new URLSearchParams(window.location.search));
      const next: IndicatorQueryState = { ...current, ...partial };
      router.replace(
        `${pathname}?${serialize(next, defaultsRef.current)}`,
        { scroll: false },
      );
    },
    [router, pathname],
  );

  return { state, patch };
}
