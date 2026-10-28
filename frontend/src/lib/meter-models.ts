import type { MeterCapabilities, MeterModel } from "./types";

/**
 * Definisi model power meter beserta kapabilitas pengukurannya.
 *
 * Sumber: datasheet masing-masing model (folder Datasheet Power Meter).
 * Ringkasan lengkap + tabel register ada di docs/parameter-specification.md.
 *
 * Kapabilitas di sini adalah kemampuan alat, sedangkan nilai yang belum dibaca
 * tetap dapat null sampai telemetry aktual diterima.
 */
export const METER_MODELS: Record<
  MeterModel,
  MeterCapabilities & {
    /** Urutan untuk display */
    label: string;
    /** Keterangan singkat */
    note: string;
  }
> = {
  "SIEMENS PAC3220": {
    label: "Siemens PAC3220",
    note: "7KM power monitoring device, 2x Ethernet + expansion module",
    perPhase: true,
    apparentEnergyRegister: true,
    thdCurrent: true,
    thdVoltage: true,
    maxHarmonicOrder: 40,
    unbalance: true,
    reactiveEnergy: true,
    demand: true,
  },
  "LOVATO DMG510": {
    label: "Lovato DMG510",
    note: "Digital multimeter, analisis harmonik s/d orde 15",
    perPhase: true,
    apparentEnergyRegister: false,
    thdCurrent: true,
    thdVoltage: true,
    maxHarmonicOrder: 15,
    unbalance: false,
    reactiveEnergy: true,
    demand: true,
  },
  "CEWE Elite440": {
    label: "CEWE Elite440",
    note: "Multi-line panel meter, THD s/d orde 31, data float IEEE754",
    perPhase: true,
    apparentEnergyRegister: false,
    thdCurrent: true,
    thdVoltage: true,
    maxHarmonicOrder: 31,
    unbalance: false,
    reactiveEnergy: true,
    demand: true,
  },
  "ACREL AMC96": {
    label: "Acrel AMC96",
    note: "Multi-function meter dengan pengukuran THD",
    perPhase: true,
    apparentEnergyRegister: false,
    thdCurrent: true,
    thdVoltage: true,
    maxHarmonicOrder: 31,
    unbalance: false,
    reactiveEnergy: true,
    demand: false,
  },
  "WEIDMULLER EM220": {
    label: "Weidmuller EM220",
    note: "THD-I tersedia; THD-U tidak tersedia. Update 1 detik",
    perPhase: true,
    apparentEnergyRegister: false,
    thdCurrent: true,
    thdVoltage: false,
    maxHarmonicOrder: 0,
    unbalance: false,
    reactiveEnergy: true,
    demand: true,
  },
};

/** Ambil kapabilitas sebuah model */
export function getCapabilities(model: MeterModel): MeterCapabilities {
  const { label: _l, note: _n, ...caps } = METER_MODELS[model];
  return caps;
}

/**
 * Ambang batas THD (IEEE 519 / IEC 61000-4-30 untuk THD tegangan).
 * Dipakai untuk menandai meter yang perlu perhatian.
 */
export const THD_THRESHOLDS = {
  /** < 3% = baik */
  good: 3,
  /** 3% - 5% = perlu perhatian */
  warning: 5,
  /** > 5% = tidak sesuai standar, berpotensi bermasalah */
  critical: 8,
} as const;

export function thdSeverity(
  thd: number | null,
): "ok" | "warning" | "critical" | "unsupported" {
  if (thd === null) return "unsupported";
  if (thd >= THD_THRESHOLDS.critical) return "critical";
  if (thd >= THD_THRESHOLDS.warning) return "warning";
  return "ok";
}

/**
 * Ambang deviasi frekuensi jaringan (IEC 61000-4-30).
 * Grid Indonesia 50 Hz; toleransi ±0,5 Hz dianggap masih normal.
 */
export const FREQUENCY_THRESHOLDS = {
  /** Frekuensi nominal grid */
  nominal: 50,
  /** Deviasi masih dianggap baik (Hz) */
  good: 0.2,
  /** Batas peringatan (Hz) */
  warning: 0.5,
  /** Batas kritis (Hz) */
  critical: 1.0,
} as const;

export function frequencySeverity(
  hz: number | null,
): "ok" | "warning" | "critical" | "unsupported" {
  if (hz === null || hz === 0) return "unsupported";
  const dev = Math.abs(hz - FREQUENCY_THRESHOLDS.nominal);
  if (dev >= FREQUENCY_THRESHOLDS.critical) return "critical";
  if (dev >= FREQUENCY_THRESHOLDS.warning) return "warning";
  return "ok";
}
