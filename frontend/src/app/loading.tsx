export default function Loading() {
  return <main aria-label="Loading FPL Kenya data" className="mx-auto min-h-[70dvh] max-w-[1500px] animate-pulse px-5 py-16 md:px-8"><div className="h-3 w-40 rounded bg-stone-950/10" /><div className="mt-7 h-20 max-w-4xl rounded bg-stone-950/10" /><div className="mt-5 h-5 max-w-2xl rounded bg-stone-950/10" /><div className="mt-16 grid grid-cols-2 gap-6 md:grid-cols-4">{Array.from({ length: 4 }).map((_, index) => <div key={index} className="h-28 rounded bg-stone-950/10" />)}</div></main>;
}
