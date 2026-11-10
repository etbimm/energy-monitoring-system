"use client";

import { usePathname } from "next/navigation";
import { LOGIN_PATH, useAuth } from "@/components/auth/auth-provider";
import { MobileNav } from "@/components/layout/mobile-nav";
import { Sidebar } from "@/components/layout/sidebar";

function FullScreenMessage({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-stone-50 px-4">
      <div className="w-full max-w-sm rounded-xl border border-stone-200 bg-white px-6 py-8 text-center text-sm text-stone-600 shadow-sm">
        {children}
      </div>
    </div>
  );
}

/**
 * Kerangka halaman: sidebar + konten untuk pengguna yang sudah login.
 * Halaman login tampil tanpa sidebar. Konten halaman baru dirender setelah
 * sesi terverifikasi, sehingga tidak ada request data tanpa login.
 */
export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { status, error, retry } = useAuth();

  if (pathname.startsWith(LOGIN_PATH)) return <>{children}</>;

  if (status === "loading") {
    return <FullScreenMessage>Memeriksa sesi login...</FullScreenMessage>;
  }
  if (status === "unauthenticated") {
    return <FullScreenMessage>Mengalihkan ke halaman login...</FullScreenMessage>;
  }
  if (status === "error") {
    return (
      <FullScreenMessage>
        <p className="font-semibold text-red-800">Backend tidak dapat dihubungi</p>
        <p className="mt-2 break-words text-xs">{error}</p>
        <button
          type="button"
          onClick={retry}
          className="mt-4 rounded-md bg-brand-700 px-4 py-2 text-xs font-semibold text-white hover:bg-brand-800"
        >
          Coba lagi
        </button>
      </FullScreenMessage>
    );
  }

  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      <Sidebar />
      <div className="flex min-h-screen min-w-0 flex-1 flex-col">
        <MobileNav />
        <main className="flex-1 overflow-x-hidden px-4 py-5 sm:px-6 md:py-6 lg:px-8">
          <div className="mx-auto max-w-7xl">{children}</div>
        </main>
        <footer className="mx-4 mb-4 flex flex-wrap items-center justify-between gap-2 rounded-lg bg-white px-6 py-4 text-xs text-slate-400 shadow-sm sm:mx-6 lg:mx-8">
          <p>
            Copyright © 2026 <span className="font-semibold text-amber-500">EMS - JWP.</span> All rights reserved.
          </p>
          <span>EMS</span>
        </footer>
      </div>
    </div>
  );
}
