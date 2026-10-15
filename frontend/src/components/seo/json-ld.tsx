/**
 * Renders one schema.org JSON-LD block. Server component: the markup is in the
 * HTML a crawler receives. "<" is escaped so a value can never close the script tag.
 */
export function JsonLd({ data }: { data: Record<string, unknown> }) {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data).replace(/</g, "\\u003c") }}
    />
  );
}
