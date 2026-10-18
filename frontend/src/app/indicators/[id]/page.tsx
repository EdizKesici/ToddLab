import type { Metadata } from "next";
import { notFound } from "next/navigation";
import IndicatorDetailView from "@/components/indicator/indicator-detail-view";
import { INDICATOR_DESCRIPTIONS } from "@/lib/toddlab/i18n/descriptions";
import { INDICATOR_LABELS_FR } from "@/lib/toddlab/i18n/labels-fr";
import { getServerDictionary } from "@/lib/toddlab/i18n/server";
import { JsonLd } from "@/components/seo/json-ld";
import { siteUrl } from "@/lib/site-url";
import { getCatalog, getIndicatorFile } from "@/lib/toddlab/store";

interface Props {
  params: Promise<{ id: string }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  const entry = getCatalog().find((i) => i.id === id);
  const { lang, d } = await getServerDictionary();
  if (!entry) {
    return { title: d.notFound.title };
  }
  // Same language as the page body: the cookie / Accept-Language decides, as for the other pages.
  if (lang === "fr") {
    const label = INDICATOR_LABELS_FR[id] ?? entry.label;
    return {
      title: label,
      description:
        INDICATOR_DESCRIPTIONS[id]?.fr ??
        `${label} sur ToddLab : chiffres officiels et estimations modélisées, classés par année, avec leur provenance complète.`,
    };
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
  return (
    <>
      <IndicatorDatasetJsonLd id={id} />
      <IndicatorDetailView />
    </>
  );
}

/**
 * schema.org Dataset for the indicator (what Google Dataset Search reads). Every
 * field comes from the published payload: label, unit, license text, declared
 * coverage and the sources' own citations. Nothing is invented.
 */
function IndicatorDatasetJsonLd({ id }: { id: string }) {
  const file = getIndicatorFile(id);
  if (!file) return null;
  const years = file.data.filter((p) => p.value !== null).map((p) => p.year);
  const start = years.length > 0 ? Math.min(...years) : file.coverage_declared.start;
  const end = years.length > 0 ? Math.max(...years) : file.coverage_declared.end;
  const description =
    INDICATOR_DESCRIPTIONS[id]?.en ??
    `${file.label} for countries of the world, with full provenance.`;
  const base = siteUrl();
  return (
    <JsonLd
      data={{
        "@context": "https://schema.org",
        "@type": "Dataset",
        name: file.label,
        description,
        url: `${base}/indicators/${id}`,
        inLanguage: "en",
        isAccessibleForFree: true,
        license: file.license,
        temporalCoverage: `${start}/${end}`,
        measurementTechnique:
          file.canonical_nature === "modelled"
            ? "Modelled estimate (the source recalculates or models the figure)"
            : "Official statistics as published by statistical services, collected as reported",
        variableMeasured: { "@type": "PropertyValue", name: file.label, unitText: file.unit },
        creator: [
          ...new Set(file.sources.map((s) => s.root_label).filter((x): x is string => Boolean(x))),
        ].map((name) => ({ "@type": "Organization", name })),
        citation: file.sources.map((s) => s.citation).filter(Boolean),
        isPartOf: { "@type": "DataCatalog", name: "ToddLab", url: base },
      }}
    />
  );
}
