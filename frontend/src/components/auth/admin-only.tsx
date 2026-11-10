"use client";

import { ShieldAlert } from "lucide-react";
import { useAuth } from "@/components/auth/auth-provider";

/** Tampilkan isi hanya untuk admin; viewer melihat pesan akses ditolak. */
export function AdminOnly({ children }: { children: React.ReactNode }) {
  const { isAdmin } = useAuth();
  if (isAdmin) return <>{children}</>;
  return (
    <div className="mx-auto mt-10 max-w-md rounded-xl border border-stone-200 bg-white px-6 py-8 text-center shadow-sm">
      <ShieldAlert className="mx-auto h-10 w-10 text-brand-600" aria-hidden />
      <p className="mt-3 text-sm font-semibold text-stone-900">Akses ditolak</p>
      <p className="mt-1 text-sm text-stone-600">Halaman ini hanya untuk admin.</p>
    </div>
  );
}
