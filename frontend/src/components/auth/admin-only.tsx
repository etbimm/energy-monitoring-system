"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth/auth-provider";

/** Tampilkan isi hanya untuk admin; arahkan viewer ke overview. */
export function AdminOnly({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { isAdmin, status } = useAuth();

  useEffect(() => {
    if (status === "authenticated" && !isAdmin) router.replace("/");
  }, [isAdmin, router, status]);

  if (isAdmin) return <>{children}</>;
  return null;
}
