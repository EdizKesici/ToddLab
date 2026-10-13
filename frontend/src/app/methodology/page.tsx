import type { Metadata } from "next";
import { MethodView } from "@/components/methodology/method-view";

export const metadata: Metadata = {
  title: "The method",
  description:
    "How ToddLab sources, keeps and shows numbers: official figures vs modelled estimates, honest gaps, the founding case of Soviet infant mortality — and why some data cannot lie.",
};

export default function MethodologyPage() {
  return <MethodView />;
}
