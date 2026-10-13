import { ImageResponse } from "next/og";
import { OgCard } from "@/components/shared/og-card";

export const size = { width: 1200, height: 630 };
export const contentType = "image/png";
export const alt = "ToddLab — social indicators, measured not declared";

export default function OpengraphImage() {
  return new ImageResponse(
    (
      <OgCard
        title="Measured, not declared."
        subtitle="Hard social indicators for every country — honest gaps, full provenance, on the method of Emmanuel Todd."
      />
    ),
    size,
  );
}
