"use client";

import Link from "next/link";
import { List, X } from "@phosphor-icons/react";
import { usePathname } from "next/navigation";
import { useState } from "react";

export const navigationItems = [
  { href: "/", label: "This gameweek" },
  { href: "/leaderboard", label: "Leaderboard" },
  { href: "/players", label: "Players" },
  { href: "/stories", label: "Weekly report" },
  { href: "/lab", label: "Data lab" },
  { href: "/methodology", label: "Methodology" },
];

function isActive(pathname: string, href: string) {
  return href === "/" ? pathname === href : pathname.startsWith(href);
}

export function DesktopNav() {
  const pathname = usePathname();
  return (
    <nav aria-label="Primary navigation" className="hidden items-center gap-1 text-sm text-stone-600 md:flex">
      {navigationItems.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          aria-current={isActive(pathname, item.href) ? "page" : undefined}
          className={`rounded-md px-3 py-2 transition duration-200 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#1f6b4d] ${
            isActive(pathname, item.href)
              ? "bg-stone-950 text-[#fffdf7]"
              : "hover:bg-stone-950/5 hover:text-stone-950"
          }`}
        >
          {item.label}
        </Link>
      ))}
    </nav>
  );
}

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
            {navigationItems.map((item) => {
              const active = isActive(pathname, item.href);
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
