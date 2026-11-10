"use client";

import { NavLinks, UserPanel } from "@/components/layout/nav-links";

export function Sidebar() {
  return (
    <aside className="hidden w-60 shrink-0 flex-col border-r border-brand-900 bg-brand-800 text-white md:sticky md:top-0 md:flex md:h-screen">
      <div className="flex items-center gap-2.5 px-5 pb-2 pt-8">
        <img
          src="/Logo%20SAMKO.jpeg"
          alt="Logo Java Wood Pellet"
          width={40}
          height={40}
          className="h-10 w-10 shrink-0 rounded-md"
        />
        <div>
          <p className="text-sm font-semibold leading-tight text-white">
            Energy Monitoring
          </p>
          <p className="text-xs leading-tight text-[#e2bd43]">
            Java Wood Pellet
          </p>
        </div>
      </div>

      <NavLinks />
      <UserPanel />
    </aside>
  );
}
