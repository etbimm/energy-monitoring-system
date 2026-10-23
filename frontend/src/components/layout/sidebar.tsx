"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  BarChart3,
  Gauge,
  LayoutDashboard,
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

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden w-60 shrink-0 flex-col border-r border-stone-200 bg-white md:sticky md:top-0 md:flex md:h-screen">
      <div className="flex items-center gap-2.5 px-5 py-5">
        <img
          src="/logo-sampoerna-kayoe.svg"
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

      <nav className="flex-1 space-y-1 overflow-y-auto px-3">
        {NAV_ITEMS.map((item) => {
          const active = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
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
  );
}