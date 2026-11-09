import { PLANT_TIME_ZONE, plantClock, plantDate } from "@/lib/time";

/** Nilai kosong (null/undefined/NaN) ditampilkan "–", bukan 0. */
export const EMPTY_VALUE = "–";

export function formatNumber(value: number | null | undefined, digits = 1): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return EMPTY_VALUE;
  return value.toLocaleString("id-ID", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

/**
 * Jam WIB (HH.mm.ss). Bila waktunya bukan hari ini (WIB), tanggal ikut
 * ditampilkan agar data lama tidak terlihat seperti data baru.
 */
export function formatTime(iso: string): string {
  if (!iso) return EMPTY_VALUE;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return EMPTY_VALUE;
  const time = date.toLocaleTimeString("id-ID", {
    timeZone: PLANT_TIME_ZONE,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
  if (plantDate(date) === plantDate()) return time;
  const day = date.toLocaleDateString("id-ID", {
    timeZone: PLANT_TIME_ZONE,
    day: "2-digit",
    month: "short",
  });
  return `${day} ${time}`;
}

export function formatDateTime(iso: string): string {
  if (!iso) return "-";
  return new Date(iso).toLocaleString("id-ID", {
    timeZone: PLANT_TIME_ZONE,
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

/** Ambil waktu WIB format HH:mm dari sebuah Date */
export function formatClock(d: Date): string {
  const { hour, minute } = plantClock(d);
  return `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
}