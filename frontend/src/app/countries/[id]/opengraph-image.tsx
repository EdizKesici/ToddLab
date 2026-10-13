import { ImageResponse } from "next/og";
import { OgCard } from "@/components/shared/og-card";
import { getEntities } from "@/lib/toddlab/store";

export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function OpengraphImage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const entity = getEntities().find((e) => e.entity_id === id);

  return new ImageResponse(
    (
      <OgCard
        title={entity?.label ?? "Country profile"}
        badge="Country profile"
        subtitle="Every indicator with the country's value, its world rank and the full series."
      />
    ),
    size,
  );
}
