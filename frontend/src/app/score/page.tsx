import { Suspense } from "react";
import type { Metadata } from "next";
import { ScoreView } from "@/components/score/score-view";

export const metadata: Metadata = {
  title: "Civilizational Score",
  description:
    "Two derived composites on a frozen absolute scale — official and modelled, never merged. Explicit weights, visible coverage, carried values labelled. Rankings by year.",
};

export default function ScorePage() {
  return (
    <Suspense>
      <ScoreView />
    </Suspense>
  );
}
