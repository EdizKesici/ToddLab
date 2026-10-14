import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { CountryView } from "@/components/country/country-view";
import { getEntities } from "@/lib/toddlab/store";

interface Props {
  params: Promise<{ id: string }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  const entity = getEntities().find((e) => e.entity_id === id);
  if (!entity) {
    return { title: "Country" };
  }
  return {
    title: entity.label,
    description: `${entity.label}'s social profile on ToddLab — every indicator with the country's value, its world rank and the full series. Official figures and modelled estimates, never mixed.`,
  };
}

export default async function CountryProfilePage({ params }: Props) {
  const { id } = await params;
  if (!getEntities().some((e) => e.entity_id === id)) notFound();
  return <CountryView />;
}
