"use client";

import { useState } from "react";
import { Menu, X } from "lucide-react";
import { NavLinks, UserPanel } from "@/components/layout/nav-links";

export function MobileNav() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <header className="sticky top-0 z-40 flex items-center gap-2.5 border-b border-brand-900 bg-brand-800 px-3 py-3 text-white md:hidden">
        <button
          type="button"
          aria-label="Buka navigasi"
          aria-expanded={isOpen}
          aria-controls="mobile-sidebar"
          onClick={() => setIsOpen(true)}
          className="rounded-md p-2 text-white/85 hover:bg-brand-700 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#e2bd43]"
        >
          <Menu className="h-5 w-5" aria-hidden />
        </button>
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
            className="fixed inset-y-0 left-0 z-50 flex w-72 max-w-[85vw] flex-col border-r border-brand-900 bg-brand-800 text-white shadow-xl"
          >
            <div className="flex items-center justify-between gap-2.5 px-5 pb-2 pt-8">
              <div className="flex items-center gap-2.5">
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
              <button
                type="button"
                aria-label="Tutup sidebar"
                onClick={() => setIsOpen(false)}
                className="rounded-md p-2 text-white/80 hover:bg-[#79221b] hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#e2bd43]"
              >
                <X className="h-5 w-5" aria-hidden />
              </button>
            </div>

            <NavLinks onNavigate={() => setIsOpen(false)} />
            <UserPanel onNavigate={() => setIsOpen(false)} />
          </aside>
        </div>
      )}
    </>
  );
}
