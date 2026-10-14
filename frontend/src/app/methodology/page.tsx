import type { Metadata } from "next";
import { MethodView } from "@/components/methodology/method-view";
import { getServerDictionary } from "@/lib/toddlab/i18n/server";

export async function generateMetadata(): Promise<Metadata> {
  const { d } = await getServerDictionary();
  return {
    title: d.method.title,
    description:
      "How ToddLab sources, keeps and shows numbers: official figures vs modelled estimates, honest gaps, the founding case of Soviet infant mortality — and why some data cannot lie.",
  };
}

export default function MethodologyPage() {
  return <MethodView />;
}
