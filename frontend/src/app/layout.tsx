import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/layout/sidebar";
import { MobileNav } from "@/components/layout/mobile-nav";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Java Wood Pellet - Energy Monitoring System",
  description: "Dashboard monitoring energi",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="id">
      <body
        className={`${geistSans.variable} ${geistMono.variable} bg-stone-50 text-stone-900 antialiased`}
      >
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
      </body>
    </html>
  );
}
