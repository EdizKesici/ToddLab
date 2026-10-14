import type { Metadata } from "next";
import { CatalogView } from "@/components/indicator/catalog-view";
import { getServerDictionary } from "@/lib/toddlab/i18n/server";
import { getCatalogMeta } from "@/lib/toddlab/store";

// Reads the backend payload at request time, so a rebuilt data/dist shows up without a frontend rebuild.
export const dynamic = "force-dynamic";

export async function generateMetadata(): Promise<Metadata> {
  const { n_indicators_available } = getCatalogMeta();
  const { d } = await getServerDictionary();
  return {
    title: d.indicators.title,
    description: `Browse ${n_indicators_available} hard social indicators — mortality, health, education, family, economy — each with its sources, coverage and honest gaps.`,
  };
}

export default function IndicatorsIndexPage() {
  return <CatalogView />;
}
