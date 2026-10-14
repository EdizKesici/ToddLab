import type { Metadata } from "next";
import ComparePageView from "@/components/compare/compare-view";
import { getServerDictionary } from "@/lib/toddlab/i18n/server";

export async function generateMetadata(): Promise<Metadata> {
  const { d } = await getServerDictionary();
  return {
    title: d.nav.compare,
    description:
      "Compare up to 12 countries across indicators, for one year or a whole period. Group synthesis, modelled estimates and book-based presets — always with provenance.",
  };
}

export default function ComparePage() {
  return <ComparePageView />;
}
