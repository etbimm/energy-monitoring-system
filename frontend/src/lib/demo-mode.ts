/**
 * Mode demo (data mock frontend) hanya aktif bila diminta secara eksplisit
 * lewat `NEXT_PUBLIC_DEMO_MODE=true`. Tanpa flag ini, kegagalan API
 * ditampilkan sebagai error dan dashboard tidak pernah menampilkan angka palsu.
 */
export const DEMO_MODE = process.env.NEXT_PUBLIC_DEMO_MODE === "true";
