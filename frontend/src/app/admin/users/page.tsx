"use client";

import { useCallback, useEffect, useState } from "react";
import { KeyRound, Pencil, Plus, UserCheck, UserX } from "lucide-react";
import { AdminOnly } from "@/components/auth/admin-only";
import { useAuth } from "@/components/auth/auth-provider";
import { PageHeader } from "@/components/layout/page-header";
import { Card } from "@/components/ui/card";
import { Alert, Button, Dialog, Field, errorMessage, inputClass } from "@/components/ui/form";
import {
  ROLE_LABEL,
  createUser,
  listUsers,
  resetUserPassword,
  updateUser,
  type User,
  type UserRole,
} from "@/lib/auth-api";
import { formatDateTime } from "@/lib/format";

type DialogState =
  | { kind: "create" }
  | { kind: "edit"; user: User }
  | { kind: "password"; user: User }
  | null;

function RoleBadge({ role }: { role: UserRole }) {
  return (
    <span
      className={
        role === "admin"
          ? "rounded-full bg-brand-100 px-2 py-0.5 text-[11px] font-semibold text-brand-800 ring-1 ring-brand-300"
          : "rounded-full bg-stone-100 px-2 py-0.5 text-[11px] font-semibold text-stone-700 ring-1 ring-stone-300"
      }
    >
      {ROLE_LABEL[role]}
    </span>
  );
}

function UserForm({
  user,
  onSaved,
  onCancel,
}: {
  user?: User;
  onSaved: (user: User) => void;
  onCancel: () => void;
}) {
  const [username, setUsername] = useState(user?.username ?? "");
  const [fullName, setFullName] = useState(user?.fullName ?? "");
  const [role, setRole] = useState<UserRole>(user?.role ?? "viewer");
  const [password, setPassword] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const saved = user
        ? await updateUser(user.id, { fullName, role })
        : await createUser({ username, fullName, role, password });
      onSaved(saved);
    } catch (cause) {
      setError(errorMessage(cause, "Gagal menyimpan akun."));
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      {error ? <Alert>{error}</Alert> : null}
      <Field
        label="Username"
        htmlFor="user-username"
        hint={user ? "Username tidak bisa diubah." : "3-32 karakter: huruf kecil, angka, titik, _ atau -"}
      >
        <input
          id="user-username"
          value={username}
          disabled={Boolean(user)}
          autoCapitalize="none"
          autoComplete="off"
          required
          onChange={(event) => setUsername(event.target.value.toLowerCase())}
          className={inputClass}
        />
      </Field>
      <Field label="Nama lengkap" htmlFor="user-fullname">
        <input
          id="user-fullname"
          value={fullName}
          required
          maxLength={80}
          onChange={(event) => setFullName(event.target.value)}
          className={inputClass}
        />
      </Field>
      <Field
        label="Role"
        htmlFor="user-role"
        hint="Viewer: hanya melihat data. Admin: kelola akun, device, dan acknowledge alarm."
      >
        <select
          id="user-role"
          value={role}
          onChange={(event) => setRole(event.target.value as UserRole)}
          className={inputClass}
        >
          <option value="viewer">Viewer</option>
          <option value="admin">Admin</option>
        </select>
      </Field>
      {!user ? (
        <Field label="Password awal" htmlFor="user-password" hint="Minimal 8 karakter, kombinasi huruf dan angka/simbol. Sampaikan ke pengguna secara langsung.">
          <input
            id="user-password"
            type="password"
            autoComplete="new-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className={inputClass}
          />
        </Field>
      ) : null}
      <div className="flex justify-end gap-2 pt-2">
        <Button variant="secondary" onClick={onCancel}>
          Batal
        </Button>
        <Button type="submit" disabled={saving}>
          {saving ? "Menyimpan..." : "Simpan"}
        </Button>
      </div>
    </form>
  );
}

function ResetPasswordForm({ user, onDone, onCancel }: { user: User; onDone: () => void; onCancel: () => void }) {
  const [password, setPassword] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await resetUserPassword(user.id, password);
      onDone();
    } catch (cause) {
      setError(errorMessage(cause, "Gagal reset password."));
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      {error ? <Alert>{error}</Alert> : null}
      <p className="text-sm text-stone-600">
        Password baru untuk <span className="font-semibold">{user.fullName}</span> (@{user.username}). Sesi login
        pengguna ini di semua perangkat akan berakhir.
      </p>
      <Field label="Password baru" htmlFor="reset-password">
        <input
          id="reset-password"
          type="password"
          autoComplete="new-password"
          required
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          className={inputClass}
        />
      </Field>
      <div className="flex justify-end gap-2 pt-2">
        <Button variant="secondary" onClick={onCancel}>
          Batal
        </Button>
        <Button type="submit" disabled={saving}>
          {saving ? "Menyimpan..." : "Reset password"}
        </Button>
      </div>
    </form>
  );
}

function UsersManager() {
  const { user: me } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [dialog, setDialog] = useState<DialogState>(null);
  const [pendingId, setPendingId] = useState<number | null>(null);

  const refresh = useCallback(async () => {
    try {
      setUsers(await listUsers());
      setError(null);
    } catch (cause) {
      setError(errorMessage(cause, "Gagal memuat daftar akun."));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  function upsert(saved: User) {
    setUsers((current) =>
      current.some((item) => item.id === saved.id)
        ? current.map((item) => (item.id === saved.id ? saved : item))
        : [...current, saved],
    );
  }

  async function toggleActive(target: User) {
    const action = target.isActive ? "menonaktifkan" : "mengaktifkan";
    if (!window.confirm(`Yakin ${action} akun ${target.fullName} (@${target.username})?`)) return;
    setPendingId(target.id);
    setNotice(null);
    try {
      upsert(await updateUser(target.id, { isActive: !target.isActive }));
      setError(null);
    } catch (cause) {
      setError(errorMessage(cause, "Gagal mengubah status akun."));
    } finally {
      setPendingId(null);
    }
  }

  return (
    <>
      <PageHeader
        title="Kelola Akun"
        description="Buat dan atur akun pengguna dashboard"
        action={
          <Button onClick={() => setDialog({ kind: "create" })}>
            <Plus className="h-4 w-4" aria-hidden />
            Tambah akun
          </Button>
        }
      />

      <div className="mb-4 space-y-2">
        {error ? <Alert>{error}</Alert> : null}
        {notice ? <Alert tone="success">{notice}</Alert> : null}
      </div>

      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="bg-stone-50 text-xs uppercase tracking-wide text-stone-500">
              <tr>
                <th className="px-4 py-3">Nama</th>
                <th className="px-4 py-3">Username</th>
                <th className="px-4 py-3">Role</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Login terakhir</th>
                <th className="px-4 py-3 text-right">Aksi</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {loading ? (
                <tr>
                  <td colSpan={6} className="px-4 py-6 text-center text-stone-500">
                    Memuat...
                  </td>
                </tr>
              ) : (
                users.map((item) => {
                  const isMe = item.id === me?.id;
                  return (
                    <tr key={item.id} className={item.isActive ? "" : "bg-stone-50 text-stone-500"}>
                      <td className="px-4 py-3 font-medium">
                        {item.fullName}
                        {isMe ? <span className="ml-2 text-[11px] text-stone-500">(Anda)</span> : null}
                      </td>
                      <td className="px-4 py-3 font-mono text-xs">{item.username}</td>
                      <td className="px-4 py-3">
                        <RoleBadge role={item.role} />
                      </td>
                      <td className="px-4 py-3">
                        {item.isActive ? (
                          <span className="text-emerald-700">Aktif</span>
                        ) : (
                          <span className="text-stone-500">Nonaktif</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-xs">
                        {item.lastLoginAt ? formatDateTime(item.lastLoginAt) : "Belum pernah"}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex justify-end gap-1.5">
                          <Button variant="secondary" onClick={() => setDialog({ kind: "edit", user: item })} title="Edit akun">
                            <Pencil className="h-3.5 w-3.5" aria-hidden />
                            Edit
                          </Button>
                          <Button
                            variant="secondary"
                            onClick={() => setDialog({ kind: "password", user: item })}
                            title="Reset password"
                          >
                            <KeyRound className="h-3.5 w-3.5" aria-hidden />
                            Password
                          </Button>
                          <Button
                            variant={item.isActive ? "danger" : "success"}
                            disabled={isMe || pendingId === item.id}
                            title={isMe ? "Tidak bisa menonaktifkan akun sendiri" : undefined}
                            onClick={() => void toggleActive(item)}
                          >
                            {item.isActive ? (
                              <UserX className="h-3.5 w-3.5" aria-hidden />
                            ) : (
                              <UserCheck className="h-3.5 w-3.5" aria-hidden />
                            )}
                            {item.isActive ? "Nonaktifkan" : "Aktifkan"}
                          </Button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </Card>

      <Dialog
        open={dialog?.kind === "create" || dialog?.kind === "edit"}
        title={dialog?.kind === "edit" ? "Edit akun" : "Tambah akun"}
        onClose={() => setDialog(null)}
      >
        {dialog?.kind === "create" || dialog?.kind === "edit" ? (
          <UserForm
            key={dialog.kind === "edit" ? dialog.user.id : "new"}
            user={dialog.kind === "edit" ? dialog.user : undefined}
            onCancel={() => setDialog(null)}
            onSaved={(saved) => {
              upsert(saved);
              setNotice(dialog.kind === "edit" ? `Akun @${saved.username} diperbarui.` : `Akun @${saved.username} dibuat.`);
              setDialog(null);
            }}
          />
        ) : null}
      </Dialog>

      <Dialog open={dialog?.kind === "password"} title="Reset password" onClose={() => setDialog(null)}>
        {dialog?.kind === "password" ? (
          <ResetPasswordForm
            user={dialog.user}
            onCancel={() => setDialog(null)}
            onDone={() => {
              setNotice(`Password @${dialog.user.username} berhasil direset.`);
              setDialog(null);
            }}
          />
        ) : null}
      </Dialog>
    </>
  );
}

export default function AdminUsersPage() {
  return (
    <AdminOnly>
      <UsersManager />
    </AdminOnly>
  );
}
