import { ImageResponse } from "next/og";
import { OgCard } from "@/components/shared/og-card";
import { getCatalog } from "@/lib/toddlab/store";

export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function OpengraphImage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const entry = getCatalog().find((i) => i.id === id);
  const label = entry?.label ?? "Indicator";
  const badge = entry?.family
    ? entry.family.charAt(0).toUpperCase() + entry.family.slice(1)
    : undefined;

  return new ImageResponse(
    (
      <OgCard
        title={label}
        badge={badge}
        subtitle="Every country, ranked by year — official figures and modelled estimates, never mixed."
      />
    ),
    size,
  );
}
