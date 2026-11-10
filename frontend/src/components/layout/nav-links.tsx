"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { KeyRound, LogOut, UserCircle2 } from "lucide-react";
import { useAuth } from "@/components/auth/auth-provider";
import { ADMIN_NAV_ITEMS, NAV_ITEMS, type NavItem } from "@/components/layout/nav-items";
import { ROLE_LABEL } from "@/lib/auth-api";
import { cn } from "@/lib/utils";

function NavLink({ item, onNavigate }: { item: NavItem; onNavigate?: () => void }) {
  const pathname = usePathname();
  const active = pathname === item.href;
  const Icon = item.icon;
  return (
    <Link
      href={item.href}
      aria-current={active ? "page" : undefined}
      onClick={onNavigate}
      className={cn(
        "flex items-center gap-3 rounded-lg border px-3 py-2 text-sm font-medium transition-colors",
        active
          ? "border-[#d3a52c] bg-brand-700 text-white"
          : "border-transparent text-white/85 hover:bg-brand-700 hover:text-white",
      )}
    >
      <Icon className="h-4 w-4" aria-hidden />
      {item.label}
    </Link>
  );
}

/** Daftar menu (umum + admin) untuk sidebar desktop dan mobile. */
export function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const { isAdmin } = useAuth();
  return (
    <nav aria-label="Navigasi utama" className="mt-2 flex-1 space-y-1 overflow-y-auto px-3">
      {NAV_ITEMS.map((item) => (
        <NavLink key={item.href} item={item} onNavigate={onNavigate} />
      ))}
      {isAdmin ? (
        <>
          <p className="px-3 pb-1 pt-4 text-[11px] font-semibold uppercase tracking-wider text-[#e2bd43]">
            Admin
          </p>
          {ADMIN_NAV_ITEMS.map((item) => (
            <NavLink key={item.href} item={item} onNavigate={onNavigate} />
          ))}
        </>
      ) : null}
    </nav>
  );
}

/** Kotak pengguna yang sedang login + ganti password + logout. */
export function UserPanel({ onNavigate }: { onNavigate?: () => void }) {
  const { user, logout } = useAuth();
  if (!user) return null;
  return (
    <div className="m-3 rounded-lg border border-white/25 bg-brand-900 px-3 py-3 text-white">
      <div className="flex items-center gap-2">
        <UserCircle2 className="h-8 w-8 shrink-0 text-[#e2bd43]" aria-hidden />
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold" title={user.fullName}>
            {user.fullName}
          </p>
          <p className="truncate text-[11px] text-white/70">
            @{user.username} · {ROLE_LABEL[user.role]}
          </p>
        </div>
      </div>
      <div className="mt-3 flex gap-2">
        {user.id !== 0 ? (
          <Link
            href="/account"
            onClick={onNavigate}
            className="flex flex-1 items-center justify-center gap-1.5 rounded-md border border-white/25 px-2 py-1.5 text-xs font-medium text-white/90 hover:bg-brand-700"
          >
            <KeyRound className="h-3.5 w-3.5" aria-hidden />
            Password
          </Link>
        ) : null}
        <button
          type="button"
          onClick={() => {
            onNavigate?.();
            void logout();
          }}
          className="flex flex-1 items-center justify-center gap-1.5 rounded-md border border-white/25 px-2 py-1.5 text-xs font-medium text-white/90 hover:bg-brand-700"
        >
          <LogOut className="h-3.5 w-3.5" aria-hidden />
          Logout
        </button>
      </div>
    </div>
  );
}
