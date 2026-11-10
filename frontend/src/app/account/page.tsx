"use client";

import { useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Alert, Button, Field, errorMessage, inputClass } from "@/components/ui/form";
import { ROLE_LABEL, changePassword } from "@/lib/auth-api";

export default function AccountPage() {
  const { user } = useAuth();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSuccess(false);
    if (next !== confirm) {
      setError("Konfirmasi password baru tidak sama.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await changePassword(current, next);
      setCurrent("");
      setNext("");
      setConfirm("");
      setSuccess(true);
    } catch (cause) {
      setError(errorMessage(cause, "Gagal mengganti password."));
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <PageHeader title="Akun Saya" description="Informasi akun dan penggantian password" />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title="Profil" />
          <CardContent>
            <dl className="grid grid-cols-[120px_1fr] gap-y-2 text-sm">
              <dt className="text-stone-500">Nama</dt>
              <dd className="font-medium">{user?.fullName}</dd>
              <dt className="text-stone-500">Username</dt>
              <dd className="font-mono">{user?.username}</dd>
              <dt className="text-stone-500">Role</dt>
              <dd>{user ? ROLE_LABEL[user.role] : "-"}</dd>
            </dl>
          </CardContent>
        </Card>

        <Card>
          <CardHeader
            title="Ganti Password"
            subtitle="Minimal 8 karakter, kombinasi huruf dan angka/simbol. Sesi di perangkat lain akan berakhir."
          />
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-3">
              {error ? <Alert>{error}</Alert> : null}
              {success ? <Alert tone="success">Password berhasil diganti.</Alert> : null}
              <Field label="Password lama" htmlFor="current-password">
                <input
                  id="current-password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={current}
                  onChange={(event) => setCurrent(event.target.value)}
                  className={inputClass}
                />
              </Field>
              <Field label="Password baru" htmlFor="new-password">
                <input
                  id="new-password"
                  type="password"
                  autoComplete="new-password"
                  required
                  minLength={8}
                  value={next}
                  onChange={(event) => setNext(event.target.value)}
                  className={inputClass}
                />
              </Field>
              <Field label="Ulangi password baru" htmlFor="confirm-password">
                <input
                  id="confirm-password"
                  type="password"
                  autoComplete="new-password"
                  required
                  value={confirm}
                  onChange={(event) => setConfirm(event.target.value)}
                  className={inputClass}
                />
              </Field>
              <Button type="submit" disabled={saving}>
                {saving ? "Menyimpan..." : "Simpan password"}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </>
  );
}
