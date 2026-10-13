"use client";

/** Gap-aware sparkline: explicit gaps (null) create line breaks — never interpolated. */
export function Sparkline({
  values,
  width = 96,
  height = 28,
  color = "var(--primary)",
  strokeWidth = 1.5,
  className,
}: {
  values: (number | null)[];
  width?: number;
  height?: number;
  color?: string;
  strokeWidth?: number;
  className?: string;
}) {
  const nums = values.filter((v): v is number => v !== null);
  if (nums.length < 2) return <svg width={width} height={height} className={className} />;

  const min = Math.min(...nums);
  const max = Math.max(...nums);
  const span = max - min || 1;
  const pad = strokeWidth + 1;
  const n = values.length;
  const x = (i: number) => (i / (n - 1)) * (width - pad * 2) + pad;
  const y = (v: number) =>
    height - pad - ((v - min) / span) * (height - pad * 2);

  // Build path segments, breaking at nulls
  const segments: string[] = [];
  let current: string[] = [];
  values.forEach((v, i) => {
    if (v === null) {
      if (current.length > 1) segments.push(current.join(" "));
      current = [];
    } else {
      current.push(
        `${current.length === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(v).toFixed(1)}`,
      );
    }
  });
  if (current.length > 1) segments.push(current.join(" "));

  return (
    <svg
      width={width}
      height={height}
      className={className}
      aria-hidden
      role="presentation"
    >
      {segments.map((d, i) => (
        <path
          key={i}
          d={d}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      ))}
      <circle
        cx={Number(
          x(values.reduce<number>((last, v, i) => (v !== null ? i : last), 0)).toFixed(
            1,
          ),
        )}
        cy={y(nums[nums.length - 1] ?? min)}
        r={strokeWidth + 0.5}
        fill={color}
      />
    </svg>
  );
}
