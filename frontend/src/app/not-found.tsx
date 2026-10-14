"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { useI18n } from "@/lib/toddlab/i18n";

/** Global 404: unknown routes and notFound() calls (unknown country / indicator ids). */
export default function NotFound() {
  const { t } = useI18n();
  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col items-center justify-center gap-6 px-4 py-24 text-center">
      <p className="font-serif text-7xl text-primary">404</p>
      <h1 className="font-serif text-3xl">{t((d) => d.notFound.title)}</h1>
      <p className="text-muted-foreground">{t((d) => d.notFound.text)}</p>
      <div className="flex flex-wrap justify-center gap-3">
        <Button asChild>
          <Link href="/">{t((d) => d.notFound.home)}</Link>
        </Button>
        <Button asChild variant="outline">
          <Link href="/countries">{t((d) => d.notFound.countries)}</Link>
        </Button>
        <Button asChild variant="outline">
          <Link href="/indicators">{t((d) => d.notFound.indicators)}</Link>
        </Button>
      </div>
    </main>
  );
}
