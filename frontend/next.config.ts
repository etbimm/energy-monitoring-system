import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,

  /**
   * Origin yang boleh mengakses resource dev (`/_next/*`).
   *
   * PENTING: Next.js mencocokkan **hostname** (tanpa port) dengan pola
   * wildcard seperti `*.example.com` — format CIDR seperti `10.0.0.0/8`
   * TIDAK dikenali dan akan diabaikan.
   *
   * Contoh yang valid: "10.23.21.*", "192.168.*.*", "localhost".
   *
   * Tanpa daftar ini, dev server memblokir (HTTP 403) permintaan
   * `/_next/*` dari perangkat lain, sehingga CSS/JS tidak termuat.
   */
  allowedDevOrigins: [
    "localhost",
    "127.0.0.1",
    "10.23.21.*", // subnet Wi-Fi lokal saat ini
    "10.*.*.*", // LAN 10.x.x.x
    "192.168.*.*", // LAN 192.168.x.x
    "172.16.*.*", // 172.16 - 172.31 (termasuk adapter WARP)
  ],
};

export default nextConfig;
