import { NextResponse, type NextRequest } from "next/server";

/**
 * Pengalihan cepat ke /login bila cookie sesi tidak ada, sebelum halaman
 * dimuat. Middleware hanya mengecek KEBERADAAN cookie (secret JWT hanya ada
 * di backend); keabsahan sesi tetap diperiksa backend di setiap request.
 *
 * Nama cookie harus sama dengan SESSION_COOKIE_NAME di backend.
 */
const SESSION_COOKIE = process.env.NEXT_PUBLIC_SESSION_COOKIE ?? "ems_session";
const DEMO_MODE = process.env.NEXT_PUBLIC_DEMO_MODE === "true";

export function middleware(request: NextRequest) {
  if (DEMO_MODE) return NextResponse.next();
  const { pathname, search } = request.nextUrl;
  if (pathname.startsWith("/login")) return NextResponse.next();
  if (request.cookies.has(SESSION_COOKIE)) return NextResponse.next();

  const url = request.nextUrl.clone();
  url.pathname = "/login";
  url.search = pathname === "/" ? "" : `?next=${encodeURIComponent(pathname + search)}`;
  return NextResponse.redirect(url);
}

export const config = {
  // Lewati aset Next.js dan file statis (logo, ikon).
  matcher: ["/((?!_next/|favicon.ico|icon.jpeg|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico)$).*)"],
};
