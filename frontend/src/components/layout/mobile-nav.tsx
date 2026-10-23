"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  BarChart3,
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

export function MobileNav() {
  const pathname = usePathname();

  return (
    <div className="sticky top-0 z-40 border-b border-stone-200 bg-white md:hidden">
      {/* Bar atas: logo */}
      <div className="flex items-center gap-2.5 px-4 py-3">
        <img
          src="/logo-sampoerna-kayoe.svg"
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
      </div>

      {/* Bar bawah: menu yang bisa di-scroll horizontal */}
      <nav className="flex gap-1 overflow-x-auto px-2 pb-2">
        {NAV_ITEMS.map((item) => {
          const active = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex shrink-0 items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors",
                active
                  ? "bg-brand-800 text-white"
                  : "bg-stone-100 text-stone-600 hover:bg-brand-50 hover:text-brand-900",
              )}
            >
              <Icon className="h-3.5 w-3.5" aria-hidden />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}