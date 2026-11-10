"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, KeyRound, Pencil, Plus, Search, Trash2, UserCheck, UserX, X } from "lucide-react";
import { AdminOnly } from "@/components/auth/admin-only";
import { useAuth } from "@/components/auth/auth-provider";
import { PageHeader } from "@/components/layout/page-header";
import { Card } from "@/components/ui/card";
import { Alert, Button, Dialog, Field, errorMessage, inputClass } from "@/components/ui/form";
import {
  ROLE_LABEL,
  createUser,
  deleteUser,
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
  | { kind: "delete"; user: User }
  | null;

/** Konfirmasi hapus permanen: admin harus mengetik ulang username. */
function DeleteUserForm({ user, onDone, onCancel }: { user: User; onDone: () => void; onCancel: () => void }) {
  const [confirmText, setConfirmText] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const matches = confirmText.trim().toLowerCase() === user.username;

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!matches) return;
    setDeleting(true);
    setError(null);
    try {
      await deleteUser(user.id);
      onDone();
    } catch (cause) {
      setError(errorMessage(cause, "Gagal menghapus akun."));
    } finally {
      setDeleting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      {error ? <Alert>{error}</Alert> : null}
      <div className="flex gap-2 rounded-lg border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-900">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
        <div className="space-y-1">
          <p>
            Akun <span className="font-semibold">{user.fullName}</span> (@{user.username}) akan{" "}
            <strong>dihapus permanen</strong> dan tidak bisa dikembalikan. Pengguna ini langsung keluar dari
            semua perangkat.
          </p>
          <p className="text-xs text-red-800">
            Riwayat aktivitasnya di Audit Log tetap tersimpan. Bila mungkin dipakai lagi nanti, cukup
            nonaktifkan akun.
          </p>
        </div>
      </div>
      <Field
        label="Konfirmasi"
        htmlFor="delete-confirm"
        hint={
          <>
            Ketik username <span className="font-mono font-semibold text-stone-800">{user.username}</span> untuk
            mengaktifkan tombol hapus.
          </>
        }
      >
        <input
          id="delete-confirm"
          value={confirmText}
          placeholder={user.username}
          autoComplete="off"
          autoCapitalize="none"
          onChange={(event) => setConfirmText(event.target.value)}
          className={`${inputClass} font-mono`}
        />
      </Field>
      <div className="flex justify-end gap-2 pt-2">
        <Button variant="secondary" onClick={onCancel}>
          Batal
        </Button>
        <Button type="submit" variant="danger" disabled={!matches || deleting}>
          <Trash2 className="h-3.5 w-3.5" aria-hidden />
          {deleting ? "Menghapus..." : "Hapus permanen"}
        </Button>
      </div>
    </form>
  );
}

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
  const [query, setQuery] = useState("");
  const [roleFilter, setRoleFilter] = useState<"all" | UserRole>("all");
  const [statusFilter, setStatusFilter] = useState<"all" | "active" | "inactive">("all");

  // Pencarian di sisi browser: daftar akun kecil, jadi tidak perlu query ke backend.
  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return users.filter((item) => {
      if (roleFilter !== "all" && item.role !== roleFilter) return false;
      if (statusFilter === "active" && !item.isActive) return false;
      if (statusFilter === "inactive" && item.isActive) return false;
      if (!needle) return true;
      return item.fullName.toLowerCase().includes(needle) || item.username.toLowerCase().includes(needle);
    });
  }, [users, query, roleFilter, statusFilter]);
  const filtering = query.trim() !== "" || roleFilter !== "all" || statusFilter !== "all";

  function resetFilters() {
    setQuery("");
    setRoleFilter("all");
    setStatusFilter("all");
  }

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
        <div className="flex flex-wrap items-center gap-3 border-b border-stone-200 px-4 py-3">
          <label className="relative min-w-0 flex-1 basis-56 sm:max-w-xs">
            <span className="sr-only">Cari akun</span>
            <Search
              className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-400"
              aria-hidden
            />
            <input
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Cari nama atau username..."
              className={`${inputClass} pl-9`}
            />
          </label>
          <label className="flex items-center gap-2 text-xs text-stone-600">
            <span>Role</span>
            <select
              value={roleFilter}
              onChange={(event) => setRoleFilter(event.target.value as "all" | UserRole)}
              className={`${inputClass} w-auto py-1.5`}
            >
              <option value="all">Semua</option>
              <option value="admin">Admin</option>
              <option value="viewer">Viewer</option>
            </select>
          </label>
          <label className="flex items-center gap-2 text-xs text-stone-600">
            <span>Status</span>
            <select
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value as "all" | "active" | "inactive")}
              className={`${inputClass} w-auto py-1.5`}
            >
              <option value="all">Semua</option>
              <option value="active">Aktif</option>
              <option value="inactive">Nonaktif</option>
            </select>
          </label>
          {filtering ? (
            <Button variant="secondary" onClick={resetFilters}>
              <X className="h-3.5 w-3.5" aria-hidden />
              Reset
            </Button>
          ) : null}
          <span className="ml-auto text-xs text-stone-500" aria-live="polite">
            {filtering ? `${visible.length} dari ${users.length} akun` : `${users.length} akun`}
          </span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[860px] text-left text-sm">
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
              ) : visible.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-6 text-center text-stone-500">
                    {filtering ? "Tidak ada akun yang cocok dengan pencarian." : "Belum ada akun."}
                  </td>
                </tr>
              ) : (
                visible.map((item) => {
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
                          <Button
                            variant="danger"
                            disabled={isMe || pendingId === item.id}
                            title={isMe ? "Tidak bisa menghapus akun sendiri" : "Hapus akun permanen"}
                            onClick={() => setDialog({ kind: "delete", user: item })}
                          >
                            <Trash2 className="h-3.5 w-3.5" aria-hidden />
                            Hapus
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

      <Dialog open={dialog?.kind === "delete"} title="Hapus akun" onClose={() => setDialog(null)}>
        {dialog?.kind === "delete" ? (
          <DeleteUserForm
            key={dialog.user.id}
            user={dialog.user}
            onCancel={() => setDialog(null)}
            onDone={() => {
              const removed = dialog.user;
              setUsers((current) => current.filter((item) => item.id !== removed.id));
              setNotice(`Akun @${removed.username} berhasil dihapus.`);
              setError(null);
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
