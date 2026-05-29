import Link from "next/link";
import { primaryManagerName, secondaryManagerName } from "@/lib/display";

const nf = new Intl.NumberFormat("en-US");

export function CompactManagerTable({
  title,
  rows,
  metricLabel,
  metricKey,
}: {
  title: string;
  rows: Array<Record<string, string | number>>;
  metricLabel: string;
  metricKey: string;
}) {
  return (
    <div className="panel rounded-lg">
      <div className="border-b border-stone-950/10 p-5">
        <h3 className="text-lg font-semibold tracking-tight">{title}</h3>
      </div>
      <div className="divide-y divide-stone-950/10">
        {rows.slice(0, 12).map((row) => (
          <Link
            href={`/managers/${row.entry}`}
            key={String(row.entry)}
            className="grid grid-cols-[3.5rem_1fr_auto] items-center gap-3 px-5 py-3 text-sm transition hover:bg-stone-950/[0.025]"
          >
            <span className="mono-num text-xs text-stone-500">#{nf.format(Number(row.rank))}</span>
            <span className="min-w-0">
              <span className="block truncate font-semibold text-stone-950">{primaryManagerName(row)}</span>
              <span className="block truncate text-xs text-stone-500">{secondaryManagerName(row)}</span>
            </span>
            <span>
              <span className="block text-right text-[10px] uppercase tracking-[0.14em] text-stone-400">
                {metricLabel}
              </span>
              <span className="mono-num block text-right font-semibold">{nf.format(Number(row[metricKey]))}</span>
            </span>
          </Link>
        ))}
      </div>
    </div>
  );
}
