import type { Metadata } from "next";
import ComparePageView from "@/components/compare/compare-view";

export const metadata: Metadata = {
  title: "Compare",
  description:
    "Compare up to 12 countries across indicators, for one year or a whole period. Group synthesis, modelled estimates and book-based presets — always with provenance.",
};

export default function ComparePage() {
  return <ComparePageView />;
}
