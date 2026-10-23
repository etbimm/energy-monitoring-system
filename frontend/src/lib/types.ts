export type DeviceStatus = "online" | "warning" | "offline";

/**
 * Peran meter terhadap hirarki panel:
 * - incoming    : sumber utama (meteran daya masuk dari grid)
 * - outcoming   : pengukuran keluar dari panel utama (subset dari incoming)
 * - distribution: panel distribusi (MCC), anak dari incoming
 */
export type MeterRole = "incoming" | "outcoming" | "distribution";

/** Model power meter yang dipakai di lapangan (lihat docs/parameter-specification.md) */
export type MeterModel =
  | "SIEMENS PAC3220"
  | "LOVATO DMG510"
  | "CEWE Elite440"
  | "ACREL AMC96"
  | "WEIDMULLER EM220";

/**
 * Kapabilitas pengukuran sebuah model power meter.
 *
 * Dipakai frontend untuk menyesuaikan tampilan: parameter yang tidak
 * didukung meter akan disembunyikan / ditandai, bukan ditampilkan kosong.
 * Sumber: datasheet masing-masing model.
 */
export interface MeterCapabilities {
  /** Pengukuran per fasa (L1/L2/L3) */
  perPhase: boolean;
  /** Register kVAh native (hanya PAC3220) */
  apparentEnergyRegister: boolean;
  /** THD arus */
  thdCurrent: boolean;
  /** THD tegangan */
  thdVoltage: boolean;
  /** Orde harmonik tertinggi yang tersedia */
  maxHarmonicOrder: number;
  /** Unbalance tegangan & arus */
  unbalance: boolean;
  /** Energi reaktif terukur (kVARh) */
  reactiveEnergy: boolean;
  /** Demand / maximum demand */
  demand: boolean;
}

/** Baris rekap power meter per tempat */
export interface MeterGroup {
  no: number;
  location: string;
  brand: string;
  model: MeterModel;
  count: number;
  role: MeterRole;
}

/**
 * Nilai per fasa (L1/L2/L3).
 *
 * Disimpan terpisah dari nilai total, bukan digabung ke tabel utama,
 * karena hanya sebagian meter yang mengukur per fasa.
 */
export interface PhaseReading {
  phase: "L1" | "L2" | "L3";
  voltage: number | null; // V
  current: number | null; // A
  power: number | null; // kW
  apparentPower: number | null; // kVA
  reactivePower: number | null; // kVAR
  powerFactor: number | null;
  thdCurrent: number | null; // %
  thdVoltage: number | null; // %
}

/**
 * Data realtime sebuah power meter.
 *
 * Pengelompokan nilai mengikuti tiga lapis yang disepakati:
 *   L1 INTI      : V, I, kW, kVA, kVAR, kWh, kVARh  -> dipoll dari meter
 *   L2 TURUNAN   : PF, kVAh                          -> dihitung di backend
 *   L3 OPSIONAL  : THD-i, THD-u, unbalance           -> hanya bila didukung
 */
export interface Device {
  id: string;
  name: string;
  location: string; // Tempat / panel induk
  brand: string; // Merk power meter
  model: MeterModel;
  role: MeterRole;
  status: DeviceStatus;
  capabilities: MeterCapabilities;

  // ---- L1: INTI (dim-poll dari meter) ----
  voltage: number; // V
  current: number; // A
  power: number; // kW  (daya aktif)
  apparentPower: number; // kVA (daya semu)
  reactivePower: number; // kVAR (daya reaktif)
  energyActive: number; // kWh
  energyReactive: number; // kVARh

  // ---- L2: TURUNAN (dihitung di backend) ----
  powerFactor: number; // kW / kVA
  energyApparent: number; // kVAh = integral kVA dt

  // ---- L3: OPSIONAL (nullable, hanya bila meter mendukung) ----
  thdCurrent: number | null; // % THD arus
  thdVoltage: number | null; // % THD tegangan
  unbalanceVoltage: number | null; // %
  unbalanceCurrent: number | null; // %

  // ---- Detail per fasa ----
  phases: PhaseReading[];

  frequency: number; // Hz
  lastSeen: string; // ISO timestamp
}

/** Panel (tempat) beserta meter-metrinya */
export interface MeterPanel {
  location: string;
  brands: string[];
  devices: Device[];
  power: number;
  apparentPower: number;
  reactivePower: number;
  energyActive: number;
}

/**
 * Satu titik data timeseries.
 *
 * `energy*` adalah nilai kumulatif register (bukan delta), karena itu yang
 * disimpan meter. Selisih antar titik dihitung di backend.
 */
export interface TimeSeriesPoint {
  timestamp: string;
  label: string;
  power: number; // kW
  apparentPower: number; // kVA
  reactivePower: number; // kVAR
  energy: number; // kWh kumulatif
  energyReactive: number; // kVARh kumulatif
  energyApparent: number; // kVAh kumulatif
  voltage: number; // V
  current: number; // A
  frequency: number; // Hz
}

export interface Alarm {
  id: string;
  timestamp: string;
  deviceId: string;
  deviceName: string;
  severity: "critical" | "warning" | "info";
  message: string;
  acknowledged: boolean;
}
