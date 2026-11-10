"use client";

import { useEffect, useRef } from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

export const inputClass =
  "w-full rounded-lg border border-stone-300 bg-white px-3 py-2 text-sm text-stone-900 outline-none " +
  "focus:border-brand-600 focus:ring-2 focus:ring-brand-200 disabled:bg-stone-100 disabled:text-stone-500";

export function Field({
  label,
  htmlFor,
  hint,
  children,
  className,
}: {
  label: string;
  htmlFor: string;
  hint?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={className}>
      <label htmlFor={htmlFor} className="mb-1 block text-xs font-semibold uppercase tracking-wide text-stone-600">
        {label}
      </label>
      {children}
      {hint ? <p className="mt-1 text-[11px] text-stone-500">{hint}</p> : null}
    </div>
  );
}

const buttonStyles = {
  primary: "bg-brand-700 text-white hover:bg-brand-800 border-transparent",
  secondary: "bg-white text-stone-700 hover:bg-stone-100 border-stone-300",
  danger: "bg-red-700 text-white hover:bg-red-800 border-transparent",
  success: "bg-emerald-700 text-white hover:bg-emerald-800 border-transparent",
} as const;

export function Button({
  variant = "primary",
  className,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: keyof typeof buttonStyles }) {
  return (
    <button
      type="button"
      className={cn(
        "inline-flex items-center justify-center gap-1.5 rounded-lg border px-3 py-2 text-xs font-semibold shadow-sm transition-colors",
        "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600",
        "disabled:cursor-not-allowed disabled:opacity-60",
        buttonStyles[variant],
        className,
      )}
      {...props}
    />
  );
}

export function Alert({
  tone = "error",
  children,
}: {
  tone?: "error" | "success";
  children: React.ReactNode;
}) {
  return (
    <p
      role={tone === "error" ? "alert" : "status"}
      className={cn(
        "rounded-lg border px-3 py-2 text-sm",
        tone === "error" ? "border-red-300 bg-red-50 text-red-800" : "border-emerald-300 bg-emerald-50 text-emerald-800",
      )}
    >
      {children}
    </p>
  );
}

/** Dialog modal sederhana (Esc / klik latar untuk menutup). */
export function Dialog({
  open,
  title,
  onClose,
  children,
  wide = false,
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  children: React.ReactNode;
  wide?: boolean;
}) {
  const panel = useRef<HTMLDivElement>(null);
  // Simpan onClose di ref: efek di bawah hanya jalan saat dialog dibuka,
  // bukan setiap render (agar fokus input tidak berpindah saat mengetik).
  const closeRef = useRef(onClose);
  closeRef.current = onClose;

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") closeRef.current();
    };
    window.addEventListener("keydown", onKey);
    panel.current
      ?.querySelector<HTMLElement>("input:not([disabled]), select:not([disabled]), textarea")
      ?.focus();
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/40 px-4 py-10">
      <button type="button" aria-label="Tutup" onClick={onClose} className="fixed inset-0 cursor-default" />
      <div
        ref={panel}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={cn("relative w-full rounded-xl bg-white shadow-xl", wide ? "max-w-2xl" : "max-w-md")}
      >
        <div className="flex items-center justify-between border-b border-stone-200 px-5 py-3">
          <h2 className="text-sm font-semibold text-stone-900">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Tutup dialog"
            className="rounded-md p-1 text-stone-500 hover:bg-stone-100 hover:text-stone-800"
          >
            <X className="h-4 w-4" aria-hidden />
          </button>
        </div>
        <div className="px-5 py-4">{children}</div>
      </div>
    </div>
  );
}

export function errorMessage(cause: unknown, fallback: string): string {
  if (cause && typeof cause === "object" && "detail" in cause && typeof cause.detail === "string") {
    return cause.detail;
  }
  return cause instanceof Error ? cause.message : fallback;
}
