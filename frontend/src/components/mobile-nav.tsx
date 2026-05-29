"use client";

import Link from "next/link";
import { List, X } from "@phosphor-icons/react";
import { usePathname } from "next/navigation";
import { useState } from "react";

const items = [
  { href: "/", label: "Overview" },
  { href: "/leaderboard", label: "Leaderboard" },
  { href: "/lab", label: "Lab" },
  { href: "/stories", label: "Stories" },
  { href: "/methodology", label: "Methodology" },
];

export function MobileNav() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();

  return (
    <div className="md:hidden">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="inline-flex size-10 items-center justify-center rounded-md border border-stone-950/10 bg-[#fffdf7] text-stone-950 transition active:translate-y-px"
        aria-expanded={open}
        aria-label={open ? "Close navigation" : "Open navigation"}
      >
        {open ? <X size={20} /> : <List size={20} />}
      </button>

      {open ? (
        <div className="absolute inset-x-3 top-[4.5rem] rounded-lg border border-stone-950/10 bg-[#fffdf7] p-2 shadow-[0_18px_50px_-32px_rgba(31,29,24,0.55)]">
          <nav className="grid gap-1 text-sm">
            {items.map((item) => {
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setOpen(false)}
                  className={`rounded-md px-3 py-3 font-medium transition ${
                    active ? "bg-stone-950 text-[#fffdf7]" : "text-stone-700 hover:bg-stone-950/5 hover:text-stone-950"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>
      ) : null}
    </div>
  );
}
