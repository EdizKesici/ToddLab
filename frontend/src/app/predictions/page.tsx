import type { Metadata } from "next";
import { PredictionsView } from "@/components/predictions/predictions-view";
import { getServerDictionary } from "@/lib/toddlab/i18n/server";
import { getPredictions } from "@/lib/toddlab/store";

// Reads the backend payload at request time, so a rebuilt data/dist shows up without a frontend rebuild.
export const dynamic = "force-dynamic";

export async function generateMetadata(): Promise<Metadata> {
  const { meta } = getPredictions();
  const { d } = await getServerDictionary();
  return {
    title: d.predictions.title,
    description: `${meta.n_predictions} predictions made by Emmanuel Todd in ${meta.n_books} of his books, listed book by book, each quotation checked against the text of the book.`,
  };
}

export default function PredictionsPage() {
  return <PredictionsView data={getPredictions()} />;
}
