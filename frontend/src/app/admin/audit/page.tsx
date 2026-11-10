"use client";

import { useCallback, useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { AdminOnly } from "@/components/auth/admin-only";
import { PageHeader } from "@/components/layout/page-header";
import { Card } from "@/components/ui/card";
import { Alert, Button, errorMessage } from "@/components/ui/form";
import { listAuditLog, type AuditEntry } from "@/lib/auth-api";
import { formatDateTime } from "@/lib/format";

const ACTION_LABEL: Record<string, string> = {
  "auth.login": "Login",
  "auth.login_failed": "Login gagal",
  "auth.change_password": "Ganti password",
  "user.create": "Buat akun",
  "user.update": "Ubah akun",
  "user.reset_password": "Reset password",
  "device.create": "Tambah device",
  "device.update": "Ubah device",
  "device.activate": "Aktifkan device",
  "device.deactivate": "Nonaktifkan device",
};

function describe(detail: Record<string, unknown>): string {
  const parts = Object.entries(detail).map(([key, value]) => {
    if (value && typeof value === "object" && "from" in value && "to" in value) {
      const change = value as { from: unknown; to: unknown };
      return `${key}: ${String(change.from ?? "-")} → ${String(change.to ?? "-")}`;
    }
    return `${key}: ${String(value ?? "-")}`;
  });
  return parts.join(", ");
}

function AuditLogView() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      setEntries(await listAuditLog(200));
      setError(null);
    } catch (cause) {
      setError(errorMessage(cause, "Gagal memuat audit log."));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return (
    <>
      <PageHeader
        title="Audit Log"
        description="200 aktivitas terakhir: login, perubahan akun, dan perubahan device"
        action={
          <Button variant="secondary" onClick={() => void refresh()} disabled={loading}>
            <RefreshCw className="h-3.5 w-3.5" aria-hidden />
            Muat ulang
          </Button>
        }
      />
      {error ? (
        <div className="mb-4">
          <Alert>{error}</Alert>
        </div>
      ) : null}
      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="bg-stone-50 text-xs uppercase tracking-wide text-stone-500">
              <tr>
                <th className="px-4 py-3">Waktu</th>
                <th className="px-4 py-3">Pengguna</th>
                <th className="px-4 py-3">Aksi</th>
                <th className="px-4 py-3">Target</th>
                <th className="px-4 py-3">Detail</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {entries.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-6 text-center text-stone-500">
                    {loading ? "Memuat..." : "Belum ada aktivitas."}
                  </td>
                </tr>
              ) : (
                entries.map((entry) => (
                  <tr key={entry.id} className={entry.action === "auth.login_failed" ? "bg-red-50/60" : ""}>
                    <td className="whitespace-nowrap px-4 py-2.5 text-xs">{formatDateTime(entry.createdAt)}</td>
                    <td className="px-4 py-2.5 font-mono text-xs">{entry.username ?? "-"}</td>
                    <td className="px-4 py-2.5 text-xs font-medium">{ACTION_LABEL[entry.action] ?? entry.action}</td>
                    <td className="px-4 py-2.5 font-mono text-xs">{entry.target ?? "-"}</td>
                    <td className="max-w-md px-4 py-2.5 text-xs text-stone-600">{describe(entry.detail)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </>
  );
}

export default function AdminAuditPage() {
  return (
    <AdminOnly>
      <AuditLogView />
    </AdminOnly>
  );
}
