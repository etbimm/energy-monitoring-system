"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  BarChart3,
  Gauge,
  LayoutDashboard,
  Menu,
  X,
  Siren,
  Cpu,
  Waves,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/realtime", label: "Real-time", icon: Activity },
  { href: "/history", label: "History", icon: BarChart3 },
  { href: "/power-quality", label: "Power Quality", icon: Waves },
  { href: "/devices", label: "Devices", icon: Cpu },
  { href: "/alarms", label: "Alarms", icon: Siren },
];

export function MobileNav() {
  const pathname = usePathname();
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <header className="sticky top-0 z-40 flex items-center gap-3 border-b border-stone-200 bg-white px-4 py-3 md:hidden">
        <button
          type="button"
          aria-label="Buka navigasi"
          aria-expanded={isOpen}
          aria-controls="mobile-sidebar"
          onClick={() => setIsOpen(true)}
          className="rounded-md p-2 text-stone-700 hover:bg-stone-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-700"
        >
          <Menu className="h-5 w-5" aria-hidden />
        </button>
        <img
          src="/Logo%20SAMKO.jpeg"
          alt="Logo Java Wood Pellet"
          width={32}
          height={32}
          className="h-8 w-8 shrink-0 rounded"
        />
        <div>
          <p className="text-sm font-semibold leading-tight text-stone-900">
            Java Wood Pellet
          </p>
          <p className="text-[11px] leading-tight text-stone-500">
            Energy Monitoring
          </p>
        </div>
      </header>

      {isOpen && (
        <div className="md:hidden">
          <button
            type="button"
            aria-label="Tutup navigasi"
            onClick={() => setIsOpen(false)}
            className="fixed inset-0 z-40 bg-black/40"
          />
          <aside
            id="mobile-sidebar"
            aria-label="Navigasi utama"
            className="fixed inset-y-0 left-0 z-50 flex w-72 max-w-[85vw] flex-col border-r border-stone-200 bg-white shadow-xl"
          >
            <div className="flex items-center justify-between gap-2.5 px-5 py-5">
              <div className="flex items-center gap-2.5">
                <img
                  src="/Logo%20SAMKO.jpeg"
                  alt="Logo Java Wood Pellet"
                  width={40}
                  height={40}
                  className="h-10 w-10 shrink-0 rounded-md"
                />
                <div>
                  <p className="text-sm font-semibold leading-tight text-stone-900">
                    Java Wood Pellet
                  </p>
                  <p className="text-[11px] leading-tight text-stone-500">
                    Energy Monitoring
                  </p>
                </div>
              </div>
              <button
                type="button"
                aria-label="Tutup sidebar"
                onClick={() => setIsOpen(false)}
                className="rounded-md p-2 text-stone-600 hover:bg-stone-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-700"
              >
                <X className="h-5 w-5" aria-hidden />
              </button>
            </div>

            <nav className="flex-1 space-y-1 overflow-y-auto px-3">
              {NAV_ITEMS.map((item) => {
                const active = pathname === item.href;
                const Icon = item.icon;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setIsOpen(false)}
                    className={cn(
                      "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                      active
                        ? "bg-brand-800 text-white"
                        : "text-stone-600 hover:bg-brand-50 hover:text-brand-900",
                    )}
                  >
                    <Icon className="h-4 w-4" aria-hidden />
                    {item.label}
                  </Link>
                );
              })}
            </nav>

            <div className="m-3 rounded-lg bg-brand-900 px-3 py-3 text-white">
              <div className="flex items-center gap-2 text-xs font-medium">
                <Gauge className="h-3.5 w-3.5" />
                <span>System normal</span>
              </div>
              <p className="mt-1 text-[11px] text-brand-200">v0.1.0 - mock data</p>
            </div>
          </aside>
        </div>
      )}
    </>
  );
}
