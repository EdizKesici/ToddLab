import "server-only";

/**
 * CSV export helpers. A file is: `# ` comment lines (provenance, licence,
 * citation: pandas reads them with `comment="#"`, `# ` lines are skipped by
 * most tools), one header row, then the data rows. RFC 4180 quoting, CRLF.
 */

export function csvCell(v: string | number | boolean | null | undefined): string {
  if (v === null || v === undefined) return "";
  const s = typeof v === "string" ? v : String(v);
  // Neutralise spreadsheet formula injection in text cells (a value never starts with = + - @ in our data, but a note might).
  const safe = typeof v === "string" && /^[=+\-@]/.test(s) ? `'${s}` : s;
  return /[",\r\n]/.test(safe) ? `"${safe.replace(/"/g, '""')}"` : safe;
}

/** One physical line per comment: newlines inside a text are folded to spaces. */
export function commentLines(lines: string[]): string {
  return lines.map((l) => `# ${l.replace(/\s*[\r\n]+\s*/g, " ").trim()}`).join("\r\n");
}

export function buildCsv(
  comments: string[],
  header: string[],
  rows: (string | number | boolean | null | undefined)[][],
): string {
  const body = [header, ...rows].map((r) => r.map(csvCell).join(",")).join("\r\n");
  return `${commentLines(comments)}\r\n${body}\r\n`;
}

export function csvResponse(csv: string, filename: string): Response {
  return new Response(csv, {
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      "Content-Disposition": `attachment; filename="${filename}"`,
      "Cache-Control": "no-store",
    },
  });
}

export function today(): string {
  return new Date().toISOString().slice(0, 10);
}
