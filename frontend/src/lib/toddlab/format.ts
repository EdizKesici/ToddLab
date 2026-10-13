/** Number formatting per ToddLab unit + shared helpers. */

const NF = {
  int: new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }),
  intEn: new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }),
  dec1: new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 1 }),
  dec1En: new Intl.NumberFormat("en-US", { maximumFractionDigits: 1 }),
  dec2: new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 2 }),
  dec2En: new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }),
  dec3: new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 3 }),
  dec3En: new Intl.NumberFormat("en-US", { maximumFractionDigits: 3 }),
};

export function fmtNumber(
  value: number | null | undefined,
  unit: string,
  locale: "fr" | "en" = "fr",
): string {
  if (value === null || value === undefined) return "";
  const en = locale === "en";
  const int = en ? NF.intEn : NF.int;
  const d1 = en ? NF.dec1En : NF.dec1;
  const d2 = en ? NF.dec2En : NF.dec2;
  const d3 = en ? NF.dec3En : NF.dec3;
  switch (unit) {
    case "year":
      return int.format(value);
    case "persons":
      return int.format(value);
    case "maternal_deaths":
      return int.format(value);
    case "pisa_score_points":
      return d1.format(value);
    case "gini_coefficient_0_to_1":
      return d3.format(value);
    case "centimeters":
      return d1.format(value);
    case "years":
      return d1.format(value);
    case "births_per_woman":
      return d2.format(value);
    case "births_per_1000_population":
      return d1.format(value);
    case "deaths_per_1000_births":
      return d1.format(value);
    case "deaths_per_100000_population":
      return d1.format(value);
    case "deaths_per_10000_vehicles":
      return d1.format(value);
    case "maternal_deaths_per_100k_live_births":
      return int.format(value);
    case "prisoners_per_100000_population":
      return int.format(value);
    case "percent":
      return d1.format(value);
    case "percent_of_live_births":
      return d1.format(value);
    default:
      return d2.format(value);
  }
}

/** Compact axis tick formatter. */
export function fmtTick(value: number, unit: string): string {
  if (unit === "persons") {
    if (Math.abs(value) >= 1_000_000) return `${(value / 1_000_000).toFixed(0)}M`;
    if (Math.abs(value) >= 1_000) return `${(value / 1_000).toFixed(0)}k`;
  }
  if (Number.isInteger(value)) return String(value);
  return String(Math.round(value * 100) / 100);
}

/** Base-100 index values: one decimal, unitless. */
export function fmtIndex(
  value: number | null | undefined,
  locale: "fr" | "en" = "fr",
): string {
  if (value === null || value === undefined) return "";
  return (locale === "en" ? NF.dec1En : NF.dec1).format(value);
}

/** Civilizational score: exactly two decimals (the backend's rounding). */
export function fmtScore(
  value: number | null | undefined,
  locale: "fr" | "en" = "fr",
): string {
  if (value === null || value === undefined) return "";
  return new Intl.NumberFormat(locale === "en" ? "en-US" : "fr-FR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

/** Coverage 0..1 → "81,3 %" / "81.3%". */
export function fmtCoverage(
  coverage: number | null | undefined,
  locale: "fr" | "en" = "fr",
): string {
  if (coverage === null || coverage === undefined) return "";
  const v = Math.round(coverage * 1000) / 10;
  return `${(locale === "en" ? NF.dec1En : NF.dec1).format(v)} %`;
}

/** Percent NUMBER only (no "%" sign) for {p} placeholders that add their own unit. */
export function fmtPct1(
  value01: number | null | undefined,
  locale: "fr" | "en" = "fr",
): string {
  if (value01 === null || value01 === undefined) return "";
  const v = Math.round(value01 * 1000) / 10;
  return (locale === "en" ? NF.dec1En : NF.dec1).format(v);
}

export function fmtPercentile(p: number): string {
  return `${Math.round(p)}`;
}

/** Which direction is "up" for this indicator. */
export function isHigherBetter(unit: string, higherIsBetter: boolean): boolean {
  return higherIsBetter;
}

/** Percentile of a value among a list of values, respecting higher_is_better → 0..100 (100 = best). */
export function percentileOf(
  value: number,
  values: number[],
  higherIsBetter: boolean,
): number {
  if (values.length === 0) return 0;
  let below = 0;
  for (const v of values) if (v < value) below++;
  const pctLow = (below / values.length) * 100;
  return higherIsBetter ? pctLow : 100 - pctLow;
}
