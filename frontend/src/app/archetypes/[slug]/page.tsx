import { CompactManagerTable } from "@/components/insight-tables";
import { SiteHeader } from "@/components/shell";
import { getArchetype } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function ArchetypePage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const rows = await getArchetype(slug);
  const label = slug.replaceAll("-", " ");

  return (
    <>
      <SiteHeader />
      <main className="mx-auto max-w-[1500px] px-5 py-10 md:px-8 md:py-16">
        <div className="mb-10 max-w-5xl">
          <div className="mono-num mb-3 text-xs uppercase tracking-[0.24em] text-[#1f6b4d]">
            Manager archetype
          </div>
          <h1 className="text-4xl font-semibold capitalize leading-none tracking-tight sm:text-5xl md:text-7xl">{label}</h1>
        </div>
        <CompactManagerTable title={`${rows.length} sampled managers`} rows={rows} metricLabel="total" metricKey="total" />
      </main>
    </>
  );
}
