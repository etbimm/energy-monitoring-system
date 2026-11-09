/**
 * Zona waktu pabrik. Semua tanggal "hari ini", rentang History, dan label jam
 * memakai WIB agar sama dengan backend (Settings.timezone), apa pun zona waktu
 * komputer/browser yang membuka dashboard. WIB tidak memakai DST (selalu +07:00).
 */
export const PLANT_TIME_ZONE = "Asia/Jakarta";
const PLANT_UTC_OFFSET = "+07:00";

const dateFormatter = new Intl.DateTimeFormat("en-CA", {
  timeZone: PLANT_TIME_ZONE,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});

const clockFormatter = new Intl.DateTimeFormat("en-GB", {
  timeZone: PLANT_TIME_ZONE,
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

/** Tanggal WIB format YYYY-MM-DD. */
export function plantDate(date: Date = new Date()): string {
  return dateFormatter.format(date);
}

/** Tanggal WIB `days` hari sebelum `date`. */
export function plantDateDaysAgo(days: number, date: Date = new Date()): string {
  return plantDate(new Date(date.getTime() - days * 86_400_000));
}

/** Awal (00:00:00) atau akhir (23:59:59.999) hari WIB, sebagai ISO UTC. */
export function plantDayBoundary(day: string, endOfDay = false): string {
  const time = endOfDay ? "23:59:59.999" : "00:00:00.000";
  return new Date(`${day}T${time}${PLANT_UTC_OFFSET}`).toISOString();
}

/** Jam & menit WIB dari sebuah waktu. */
export function plantClock(date: Date): { hour: number; minute: number } {
  const [hour, minute] = clockFormatter.format(date).split(":").map(Number);
  return { hour, minute };
}
