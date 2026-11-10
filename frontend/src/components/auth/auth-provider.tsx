"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { usePathname, useRouter } from "next/navigation";
import { ApiError, setUnauthorizedHandler } from "@/lib/api";
import { getMe, logout as apiLogout, type User } from "@/lib/auth-api";
import { DEMO_MODE } from "@/lib/demo-mode";

type AuthStatus = "loading" | "authenticated" | "unauthenticated" | "error";

interface AuthContextValue {
  user: User | null;
  status: AuthStatus;
  error: string | null;
  isAdmin: boolean;
  /** Dipanggil halaman login setelah berhasil. */
  setUser: (user: User) => void;
  logout: () => Promise<void>;
  retry: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

/** Pengguna tiruan saat mode demo dan backend tidak terjangkau. */
const DEMO_USER: User = {
  id: 0,
  username: "demo",
  fullName: "Mode Demo",
  role: "viewer",
  isActive: true,
  lastLoginAt: null,
  createdAt: null,
};

export const LOGIN_PATH = "/login";

/** Hanya path internal yang boleh jadi tujuan setelah login (cegah open redirect). */
export function safeNextPath(value: string | null | undefined): string {
  if (!value || !value.startsWith("/") || value.startsWith("//") || value.startsWith(LOGIN_PATH)) {
    return "/";
  }
  return value;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUserState] = useState<User | null>(null);
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const pathnameRef = useRef(pathname);
  pathnameRef.current = pathname;

  const goToLogin = useCallback(() => {
    const current = pathnameRef.current;
    if (current.startsWith(LOGIN_PATH)) return;
    const next = encodeURIComponent(current + window.location.search);
    router.replace(`${LOGIN_PATH}?next=${next}`);
  }, [router]);

  // Cek sesi saat aplikasi dibuka (dan saat tombol "Coba lagi" ditekan).
  useEffect(() => {
    let cancelled = false;
    setStatus("loading");
    getMe()
      .then((me) => {
        if (cancelled) return;
        setUserState(me);
        setStatus("authenticated");
        setError(null);
      })
      .catch((cause: unknown) => {
        if (cancelled) return;
        if (cause instanceof ApiError && cause.status === 401) {
          setUserState(null);
          setStatus("unauthenticated");
          setError(null);
          return;
        }
        if (DEMO_MODE) {
          setUserState(DEMO_USER);
          setStatus("authenticated");
          return;
        }
        setUserState(null);
        setStatus("error");
        setError(cause instanceof Error ? cause.message : "Gagal memeriksa sesi login.");
      });
    return () => {
      cancelled = true;
    };
  }, [attempt]);

  // Belum login: arahkan ke halaman login.
  useEffect(() => {
    if (status === "unauthenticated") goToLogin();
  }, [status, pathname, goToLogin]);

  // Sesi habis/dicabut saat sedang dipakai (API membalas 401).
  useEffect(() => {
    setUnauthorizedHandler(() => {
      setUserState(null);
      setStatus("unauthenticated");
    });
    return () => setUnauthorizedHandler(null);
  }, []);

  const setUser = useCallback((next: User) => {
    setUserState(next);
    setStatus("authenticated");
    setError(null);
  }, []);

  const logout = useCallback(async () => {
    try {
      await apiLogout();
    } catch {
      // Tetap keluar di sisi tampilan walau backend tidak terjangkau.
    }
    // Efek di atas mengarahkan ke halaman login.
    setUserState(null);
    setStatus("unauthenticated");
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      status,
      error,
      isAdmin: user?.role === "admin",
      setUser,
      logout,
      retry: () => setAttempt((n) => n + 1),
    }),
    [user, status, error, setUser, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth harus dipakai di dalam <AuthProvider>.");
  return context;
}
