"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Eye, EyeOff, LogIn } from "lucide-react";
import { safeNextPath, useAuth } from "@/components/auth/auth-provider";
import { ApiError } from "@/lib/api";
import { getMe, login } from "@/lib/auth-api";

function LoginForm() {
  const params = useSearchParams();
  const next = safeNextPath(params.get("next"));
  const { status, setUser } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Sudah login (mis. membuka /login lewat bookmark): langsung ke dashboard.
  useEffect(() => {
    if (status === "authenticated") window.location.replace(next);
  }, [status, next]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!username.trim() || !password) {
      setError("Username dan password wajib diisi.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await login(username.trim(), password);
      // Pastikan cookie sesi benar-benar tersimpan dan terkirim kembali.
      let me;
      try {
        me = await getMe();
      } catch {
        setError(
          "Login berhasil, tetapi cookie sesi tidak tersimpan. Buka dashboard dengan " +
            "alamat host yang sama dengan backend (mis. keduanya localhost atau keduanya IP yang sama).",
        );
        return;
      }
      setUser(me);
      // Navigasi penuh agar middleware membaca cookie sesi yang baru.
      window.location.replace(next);
    } catch (cause) {
      if (cause instanceof ApiError) {
        setError(cause.detail);
      } else {
        setError(cause instanceof Error ? cause.message : "Login gagal.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4" noValidate>
      {error ? (
        <p role="alert" className="rounded-lg border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-800">
          {error}
        </p>
      ) : null}

      <div>
        <label htmlFor="username" className="mb-1 block text-xs font-semibold uppercase tracking-wide text-stone-600">
          Username
        </label>
        <input
          id="username"
          name="username"
          autoComplete="username"
          autoCapitalize="none"
          autoFocus
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          className="w-full rounded-lg border border-stone-300 px-3 py-2 text-sm outline-none focus:border-brand-600 focus:ring-2 focus:ring-brand-200"
        />
      </div>

      <div>
        <label htmlFor="password" className="mb-1 block text-xs font-semibold uppercase tracking-wide text-stone-600">
          Password
        </label>
        <div className="relative">
          <input
            id="password"
            name="password"
            type={showPassword ? "text" : "password"}
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="w-full rounded-lg border border-stone-300 px-3 py-2 pr-10 text-sm outline-none focus:border-brand-600 focus:ring-2 focus:ring-brand-200"
          />
          <button
            type="button"
            onClick={() => setShowPassword((value) => !value)}
            aria-label={showPassword ? "Sembunyikan password" : "Tampilkan password"}
            className="absolute inset-y-0 right-0 flex items-center px-3 text-stone-500 hover:text-stone-800"
          >
            {showPassword ? <EyeOff className="h-4 w-4" aria-hidden /> : <Eye className="h-4 w-4" aria-hidden />}
          </button>
        </div>
      </div>

      <button
        type="submit"
        disabled={submitting}
        className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand-700 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-brand-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        <LogIn className="h-4 w-4" aria-hidden />
        {submitting ? "Memproses..." : "Masuk"}
      </button>

      <p className="text-center text-xs text-stone-500">
        Belum punya akun atau lupa password? Hubungi admin EMS.
      </p>
    </form>
  );
}

export default function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-brand-800 px-4 py-10">
      <div className="w-full max-w-sm rounded-2xl bg-white p-6 shadow-xl sm:p-8">
        <div className="mb-6 flex items-center gap-3">
          <img
            src="/Logo%20SAMKO.jpeg"
            alt="Logo Java Wood Pellet"
            width={48}
            height={48}
            className="h-12 w-12 shrink-0 rounded-md"
          />
          <div>
            <h1 className="text-lg font-bold leading-tight text-[#8d1c1c]">Energy Monitoring</h1>
            <p className="text-xs text-stone-500">Java Wood Pellet · Silakan login</p>
          </div>
        </div>
        <Suspense fallback={<p className="text-sm text-stone-500">Memuat...</p>}>
          <LoginForm />
        </Suspense>
      </div>
    </div>
  );
}
