"use client";

import { Hero } from "@/components/home/hero";
import { ScoreTeaser } from "@/components/score/score-teaser";
import { StatsBand } from "@/components/home/stats-band";
import { TeaserCards } from "@/components/home/teaser-cards";

export default function HomePage() {
  return (
    <div>
      <div className="mx-auto w-full max-w-6xl px-4 sm:px-6 lg:px-8">
        <Hero />
      </div>

      <StatsBand />

      <div className="mx-auto w-full max-w-6xl px-4 py-16 sm:px-6 sm:py-20 lg:px-8">
        <TeaserCards />
        <div className="mt-6 sm:mt-8">
          <ScoreTeaser />
        </div>
      </div>
    </div>
  );
}
