import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { CountryView } from "@/components/country/country-view";
import { ENTITY_LABELS_FR } from "@/lib/toddlab/i18n/labels-fr";
import { getServerDictionary } from "@/lib/toddlab/i18n/server";
import { getEntities } from "@/lib/toddlab/store";

interface Props {
  params: Promise<{ id: string }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  const entity = getEntities().find((e) => e.entity_id === id);
  const { lang, d } = await getServerDictionary();
  if (!entity) {
    return { title: d.notFound.title };
  }
  if (lang === "fr") {
    const label = ENTITY_LABELS_FR[id] ?? entity.label;
    return {
      title: label,
      description: `Profil social de ${label} sur ToddLab : chaque indicateur avec la valeur du pays, son rang mondial et la série complète. Chiffres officiels et estimations modélisées, jamais mélangés.`,
    };
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
