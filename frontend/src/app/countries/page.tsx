import type { Metadata } from "next";
import { CountriesView } from "@/components/country/countries-view";
import { getEntities } from "@/lib/toddlab/store";

// Reads the backend payload at request time, so a rebuilt data/dist shows up without a frontend rebuild.
export const dynamic = "force-dynamic";

export async function generateMetadata(): Promise<Metadata> {
  const n = getEntities().length;
  return {
    title: "Countries & entities",
    description: `${n} countries and entities — including former states — each with its full indicator profile: ranks, series and history.`,
  };
}

export default function CountriesIndexPage() {
  return <CountriesView />;
}
