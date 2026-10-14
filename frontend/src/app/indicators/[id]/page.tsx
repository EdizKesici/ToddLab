import type { Metadata } from "next";
import { notFound } from "next/navigation";
import IndicatorDetailView from "@/components/indicator/indicator-detail-view";
import { INDICATOR_DESCRIPTIONS } from "@/lib/toddlab/i18n/descriptions";
import { getCatalog } from "@/lib/toddlab/store";

interface Props {
  params: Promise<{ id: string }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  const entry = getCatalog().find((i) => i.id === id);
  if (!entry) {
    return { title: "Indicator" };
  }
  const description =
    INDICATOR_DESCRIPTIONS[id]?.en ??
    `${entry.label} on ToddLab — official figures and modelled estimates, ranked by year, with full provenance.`;
  return {
    title: entry.label,
    description,
  };
}

export default async function IndicatorDetailPage({ params }: Props) {
  const { id } = await params;
  if (!getCatalog().some((i) => i.id === id)) notFound();
  return <IndicatorDetailView />;
}
