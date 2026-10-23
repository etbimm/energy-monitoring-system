import type {
  Alarm,
  Device,
  MeterGroup,
  MeterPanel,
  MeterRole,
  DeviceStatus,
  PhaseReading,
  TimeSeriesPoint,
} from "./types";
import { getCapabilities } from "./meter-models";

/**
 * MOCK DATA — hanya untuk development frontend.
 * Nanti bagian ini diganti dengan fetch ke backend API.
 *
 * Rekap power meter (18 unit) sesuai data lapangan:
 *   LVMDP          - SIEMENS PAC3220 (Incoming)   5
 *   LVMDP          - LOVATO DMG510 (Outcoming)    3
 *   MVMDP          - CEWE Elite440                 1
 *   MCC 1..4       - ACREL AMC96                   6
 *   MCC Pellet 1-3 - WEIDMULLER EM220              3
 *
 * Nilai kVA & kVAR diturunkan dari kW & PF agar konsisten secara listrik:
 *   kVA  = kW / PF
 *   kVAR = kW * tan(acos(PF))
 */

/** Rekap per tempat (sesuai tabel yang diberikan) */
export const METER_GROUPS: MeterGroup[] = [
  { no: 1, location: "LVMDP", brand: "SIEMENS PAC3220", model: "SIEMENS PAC3220", count: 5, role: "incoming" },
  { no: 2, location: "LVMDP", brand: "LOVATO DMG510", model: "LOVATO DMG510", count: 3, role: "outcoming" },
  { no: 3, location: "MVMDP", brand: "Elite440", model: "CEWE Elite440", count: 1, role: "incoming" },
  { no: 4, location: "MCC 1", brand: "Acrel AMC96", model: "ACREL AMC96", count: 2, role: "distribution" },
  { no: 5, location: "MCC 2", brand: "Acrel AMC96", model: "ACREL AMC96", count: 1, role: "distribution" },
  { no: 6, location: "MCC 3", brand: "Acrel AMC96", model: "ACREL AMC96", count: 2, role: "distribution" },
  { no: 7, location: "MCC 4", brand: "Acrel AMC96", model: "ACREL AMC96", count: 1, role: "distribution" },
  { no: 8, location: "MCC Pellet 1", brand: "Weidmuller EM220", model: "WEIDMULLER EM220", count: 1, role: "distribution" },
  { no: 9, location: "MCC Pellet 2", brand: "Weidmuller EM220", model: "WEIDMULLER EM220", count: 1, role: "distribution" },
  { no: 10, location: "MCC Pellet 3", brand: "Weidmuller EM220", model: "WEIDMULLER EM220", count: 1, role: "distribution" },
];

export const TOTAL_METERS = METER_GROUPS.reduce((s, g) => s + g.count, 0); // 18

/**
 * Waktu acuan. Dipotong ke menit supaya nilai `lastSeen` sama di server dan
 * client (tidak memicu hydration mismatch).
 */
const NOW = (() => {
  const d = new Date();
  d.setSeconds(0, 0);
  return d;
})();

interface MeterSpec {
  id: string;
  name: string;
  location: string;
  model: Device["model"];
  role: MeterRole;
  status: DeviceStatus;
  power: number; // kW
  powerFactor: number;
  energyActive: number; // kWh
  voltage: number; // V
  current: number; // A
  frequency: number; // Hz
  /** THD arus (%) — null bila meter tidak mendukung / opsi belum terpasang */
  thdCurrent?: number | null;
  /** THD tegangan (%) */
  thdVoltage?: number | null;
  unbalanceVoltage?: number | null;
  unbalanceCurrent?: number | null;
  /** menit sejak terakhir communicate (hanya untuk meter offline) */
  offlineMinutes?: number;
}

const METER_SPECS: MeterSpec[] = [
  // ---- LVMDP - SIEMENS PAC3220 (Incoming) ----
  { id: "PM-LVMDP-IN-01", name: "LVMDP Incoming 1", location: "LVMDP", model: "SIEMENS PAC3220", role: "incoming", status: "online", power: 118.6, powerFactor: 0.94, energyActive: 1421.3, voltage: 400.2, current: 182.4, frequency: 50.01, thdCurrent: 2.4, thdVoltage: 1.3, unbalanceVoltage: 0.6, unbalanceCurrent: 1.8 },
  { id: "PM-LVMDP-IN-02", name: "LVMDP Incoming 2", location: "LVMDP", model: "SIEMENS PAC3220", role: "incoming", status: "online", power: 74.2, powerFactor: 0.92, energyActive: 889.4, voltage: 399.7, current: 113.1, frequency: 49.98, thdCurrent: 3.1, thdVoltage: 1.6, unbalanceVoltage: 0.9, unbalanceCurrent: 2.4 },
  { id: "PM-LVMDP-IN-03", name: "LVMDP Incoming 3", location: "LVMDP", model: "SIEMENS PAC3220", role: "incoming", status: "warning", power: 52.8, powerFactor: 0.88, energyActive: 633.6, voltage: 402.8, current: 80.4, frequency: 50.03, thdCurrent: 6.2, thdVoltage: 2.4, unbalanceVoltage: 1.8, unbalanceCurrent: 5.1 },
  { id: "PM-LVMDP-IN-04", name: "LVMDP Incoming 4", location: "LVMDP", model: "SIEMENS PAC3220", role: "incoming", status: "online", power: 33.1, powerFactor: 0.93, energyActive: 397.2, voltage: 398.9, current: 50.4, frequency: 50.0, thdCurrent: 2.7, thdVoltage: 1.4, unbalanceVoltage: 0.5, unbalanceCurrent: 1.2 },
  { id: "PM-LVMDP-IN-05", name: "LVMDP Incoming 5", location: "LVMDP", model: "SIEMENS PAC3220", role: "incoming", status: "online", power: 21.3, powerFactor: 0.9, energyActive: 255.6, voltage: 401.1, current: 32.5, frequency: 49.99, thdCurrent: 2.2, thdVoltage: 1.2, unbalanceVoltage: 0.4, unbalanceCurrent: 1.5 },
  // ---- LVMDP - LOVATO DMG510 (Outcoming) ----
  { id: "PM-LVMDP-OUT-01", name: "LVMDP Outcoming 1", location: "LVMDP", model: "LOVATO DMG510", role: "outcoming", status: "online", power: 96.4, powerFactor: 0.91, energyActive: 1156.8, voltage: 399.5, current: 146.9, frequency: 50.02, thdCurrent: 3.8, thdVoltage: 1.9 },
  { id: "PM-LVMDP-OUT-02", name: "LVMDP Outcoming 2", location: "LVMDP", model: "LOVATO DMG510", role: "outcoming", status: "online", power: 71.8, powerFactor: 0.9, energyActive: 861.6, voltage: 400.1, current: 109.4, frequency: 49.97, thdCurrent: 4.2, thdVoltage: 2.1 },
  { id: "PM-LVMDP-OUT-03", name: "LVMDP Outcoming 3", location: "LVMDP", model: "LOVATO DMG510", role: "outcoming", status: "online", power: 55.2, powerFactor: 0.92, energyActive: 662.4, voltage: 401.4, current: 84.1, frequency: 50.01, thdCurrent: 3.4, thdVoltage: 1.7 },
  // ---- MVMDP - CEWE Elite440 ----
  { id: "PM-MVMDP-01", name: "MVMDP", location: "MVMDP", model: "CEWE Elite440", role: "incoming", status: "online", power: 64.5, powerFactor: 0.95, energyActive: 774.0, voltage: 398.4, current: 98.3, frequency: 50.02, thdCurrent: 5.8, thdVoltage: 2.9 },
  // ---- MCC 1 - ACREL AMC96 (tanpa opsi /H -> tidak ada THD) ----
  { id: "PM-MCC1-01", name: "MCC 1 Meter 1", location: "MCC 1", model: "ACREL AMC96", role: "distribution", status: "online", power: 42.6, powerFactor: 0.9, energyActive: 511.2, voltage: 399.1, current: 64.9, frequency: 49.99, thdCurrent: null, thdVoltage: null },
  { id: "PM-MCC1-02", name: "MCC 1 Meter 2", location: "MCC 1", model: "ACREL AMC96", role: "distribution", status: "warning", power: 38.2, powerFactor: 0.89, energyActive: 458.4, voltage: 398.7, current: 58.2, frequency: 50.0, thdCurrent: null, thdVoltage: null },
  // ---- MCC 2 - ACREL AMC96 (opsi /H terpasang -> THD tersedia) ----
  { id: "PM-MCC2-01", name: "MCC 2 Meter 1", location: "MCC 2", model: "ACREL AMC96", role: "distribution", status: "online", power: 29.4, powerFactor: 0.88, energyActive: 352.8, voltage: 400.3, current: 44.8, frequency: 50.01, thdCurrent: 4.1, thdVoltage: 2.2 },
  // ---- MCC 3 - ACREL AMC96 ----
  { id: "PM-MCC3-01", name: "MCC 3 Meter 1", location: "MCC 3", model: "ACREL AMC96", role: "distribution", status: "online", power: 31.7, powerFactor: 0.91, energyActive: 380.4, voltage: 399.6, current: 48.3, frequency: 49.98, thdCurrent: null, thdVoltage: null },
  { id: "PM-MCC3-02", name: "MCC 3 Meter 2", location: "MCC 3", model: "ACREL AMC96", role: "distribution", status: "online", power: 27.3, powerFactor: 0.9, energyActive: 327.6, voltage: 400.8, current: 41.6, frequency: 50.02, thdCurrent: null, thdVoltage: null },
  // ---- MCC 4 - ACREL AMC96 (offline) ----
  { id: "PM-MCC4-01", name: "MCC 4 Meter 1", location: "MCC 4", model: "ACREL AMC96", role: "distribution", status: "offline", power: 0, powerFactor: 0, energyActive: 0, voltage: 0, current: 0, frequency: 0, thdCurrent: null, thdVoltage: null, offlineMinutes: 42 },
  // ---- MCC Pellet 1 - WEIDMULLER EM220 (BasicLine, tanpa harmonik) ----
  { id: "PM-PEL1-01", name: "MCC Pellet 1", location: "MCC Pellet 1", model: "WEIDMULLER EM220", role: "distribution", status: "online", power: 26.5, powerFactor: 0.93, energyActive: 318.0, voltage: 399.2, current: 40.4, frequency: 50.01, thdCurrent: null, thdVoltage: null },
  // ---- MCC Pellet 2 - WEIDMULLER EM220 ----
  { id: "PM-PEL2-01", name: "MCC Pellet 2", location: "MCC Pellet 2", model: "WEIDMULLER EM220", role: "distribution", status: "online", power: 24.1, powerFactor: 0.92, energyActive: 289.2, voltage: 398.6, current: 36.7, frequency: 49.99, thdCurrent: null, thdVoltage: null },
  // ---- MCC Pellet 3 - WEIDMULLER EM220 ----
  { id: "PM-PEL3-01", name: "MCC Pellet 3", location: "MCC Pellet 3", model: "WEIDMULLER EM220", role: "distribution", status: "online", power: 28.9, powerFactor: 0.94, energyActive: 346.8, voltage: 400.5, current: 44.0, frequency: 50.03, thdCurrent: null, thdVoltage: null },
];

/**
 * PRNG deterministik (mulberry32).
 * Dipakai supaya data mock IDENTIK di server dan client,
 * sehingga tidak terjadi hydration mismatch.
 * Nanti diganti data asli dari backend.
 */
function seededRandom(seed: number) {
  let a = seed >>> 0;
  return function () {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function hashSeed(text: string): number {
  return text.split("").reduce((s, c) => s + c.charCodeAt(0), 0) * 2654435761;
}

/** kVAR = kW * tan(acos(PF)) */
function reactiveFromPF(power: number, pf: number): number {
  if (pf <= 0 || pf >= 1) return 0;
  return power * Math.tan(Math.acos(pf));
}

/**
 * Bangun pembacaan per fasa (L1/L2/L3) yang konsisten dengan nilai total.
 * Pembagian antar fasa dibobot acak deterministik lalu dinormalisasi,
 * sehingga jumlah fasa selalu sama dengan nilai total.
 */
function buildPhases(spec: MeterSpec): PhaseReading[] {
  const rand = seededRandom(hashSeed(spec.id));
  const weights = [0, 1, 2].map(() => 0.3 + rand() * 0.08);
  const sum = weights.reduce((a, b) => a + b, 0);
  const norm = weights.map((w) => w / sum);

  const phases: ("L1" | "L2" | "L3")[] = ["L1", "L2", "L3"];

  return phases.map((phase, i) => {
    if (spec.status === "offline") {
      return {
        phase,
        voltage: null,
        current: null,
        power: null,
        apparentPower: null,
        reactivePower: null,
        powerFactor: null,
        thdCurrent: null,
        thdVoltage: null,
      };
    }

    const voltage = round1(spec.voltage + (rand() - 0.5) * 2.2);
    const current = round1(spec.current * norm[i]);
    const power = round1(spec.power * norm[i]);
    const apparentPower = round1(power / (spec.powerFactor || 1));

    return {
      phase,
      voltage,
      current,
      power,
      apparentPower,
      reactivePower: round1(reactiveFromPF(power, spec.powerFactor)),
      powerFactor: spec.powerFactor,
      thdCurrent:
        spec.thdCurrent === null || spec.thdCurrent === undefined
          ? null
          : round1(spec.thdCurrent + (rand() - 0.5) * 1.2),
      thdVoltage:
        spec.thdVoltage === null || spec.thdVoltage === undefined
          ? null
          : round1(spec.thdVoltage + (rand() - 0.5) * 0.6),
    };
  });
}

function round1(n: number): number {
  return Math.round(n * 10) / 10;
}

function round2(n: number): number {
  return Math.round(n * 100) / 100;
}

export const DEVICES: Device[] = METER_SPECS.map((m) => {
  const apparentPower = m.powerFactor > 0 ? m.power / m.powerFactor : 0;
  const reactivePower = reactiveFromPF(m.power, m.powerFactor);
  const offline = m.status === "offline";

  return {
    id: m.id,
    name: m.name,
    location: m.location,
    brand: METER_GROUPS.find(
      (g) => g.location === m.location && g.model === m.model,
    )?.brand ?? m.model,
    model: m.model,
    role: m.role,
    status: m.status,
    capabilities: getCapabilities(m.model),

    // L1 INTI
    voltage: m.voltage,
    current: m.current,
    power: m.power,
    apparentPower: round1(apparentPower),
    reactivePower: round1(reactivePower),
    energyActive: m.energyActive,
    energyReactive: round1(m.energyActive * (reactivePower / (m.power || 1)) * 0.85),

    // L2 TURUNAN
    powerFactor: m.powerFactor,
    energyApparent: round1(m.powerFactor > 0 ? m.energyActive / m.powerFactor : 0),

    // L3 OPSIONAL
    thdCurrent: offline ? null : (m.thdCurrent ?? null),
    thdVoltage: offline ? null : (m.thdVoltage ?? null),
    unbalanceVoltage: offline ? null : (m.unbalanceVoltage ?? null),
    unbalanceCurrent: offline ? null : (m.unbalanceCurrent ?? null),

    phases: buildPhases(m),

    frequency: m.frequency,
    lastSeen: offline
      ? new Date(NOW.getTime() - (m.offlineMinutes ?? 0) * 60_000).toISOString()
      : NOW.toISOString(),
  };
});

/**
 * Generate 24 jam data consumption dengan pola load harian yang realistis:
 * rendah saat malam, naik pagi, peak siang (produksi), turun sore/malam.
 */
export function generateDailyProfile(): TimeSeriesPoint[] {
  const points: TimeSeriesPoint[] = [];
  const now = new Date();
  const start = new Date(now);
  start.setHours(0, 0, 0, 0);

  let cumulativeEnergy = 0;
  let cumulativeReactive = 0;
  let cumulativeApparent = 0;

  for (let h = 0; h < 24; h++) {
    const d = new Date(start);
    d.setHours(h);

    // kurva load harian (0..1)
    const shape = loadShape(h);
    const jitter = 0.92 + Math.random() * 0.16; // variasi kecil
    const power = Math.max(8, shape * 400 * jitter);
    const pf = 0.88 + Math.random() * 0.07; // PF memburuk saat beban rendah
    const apparentPower = power / pf;
    const reactivePower = reactiveFromPF(power, pf);

    // kWh akumulatif: power(kW) * 1 jam
    cumulativeEnergy += power * 1;
    cumulativeReactive += reactivePower * 1;
    cumulativeApparent += apparentPower * 1;

    points.push({
      timestamp: d.toISOString(),
      label: `${String(h).padStart(2, "0")}:00`,
      power: round1(power),
      apparentPower: round1(apparentPower),
      reactivePower: round1(reactivePower),
      energy: round1(cumulativeEnergy),
      energyReactive: round1(cumulativeReactive),
      energyApparent: round1(cumulativeApparent),
      voltage: 398 + Math.random() * 5,
      current: round1((power * 1000) / (380 * 1.732 * 0.93)),
      frequency: round2(50 + (Math.random() - 0.5) * 0.06),
    });
  }

  return points;
}

function loadShape(hour: number): number {
  if (hour < 6) return 0.15;
  if (hour < 8) return 0.35;
  if (hour < 11) return 0.7;
  if (hour < 14) return 0.95; // peak produksi siang
  if (hour < 17) return 0.85;
  if (hour < 20) return 0.5;
  return 0.25;
}

/**
 * Generate data historis sesuai rentang tanggal.
 * - rentang <= 2 hari  -> bucket per jam
 * - rentang <= 60 hari -> bucket per hari
 * - di atasnya         -> bucket per minggu
 *
 * Ini meniru perilaku downsampling yang akan dilakukan backend + TimescaleDB.
 */
export function generateProfileForRange(
  fromStr: string,
  toStr: string,
): TimeSeriesPoint[] {
  const from = new Date(`${fromStr}T00:00:00`);
  const to = new Date(`${toStr}T23:59:59`);
  const days = Math.max(1, Math.round((to.getTime() - from.getTime()) / 86400_000));

  // seed tetap dari rentang tanggal agar konsisten antar render
  const rand = seededRandom(
    fromStr.split("").reduce((s, c) => s + c.charCodeAt(0), 0) * 31 + days,
  );

  const points: TimeSeriesPoint[] = [];
  let cumulativeEnergy = 0;
  let cumulativeReactive = 0;
  let cumulativeApparent = 0;

  if (days <= 2) {
    for (let t = from.getTime(); t <= to.getTime(); t += 3600_000) {
      const d = new Date(t);
      const hour = d.getHours();
      const power = Math.max(8, loadShape(hour) * 400 * (0.92 + rand() * 0.16));
      const pf = 0.88 + rand() * 0.07;
      const apparentPower = power / pf;
      const reactivePower = reactiveFromPF(power, pf);

      cumulativeEnergy += power;
      cumulativeReactive += reactivePower;
      cumulativeApparent += apparentPower;

      points.push({
        timestamp: d.toISOString(),
        label: `${String(hour).padStart(2, "0")}:00`,
        power: round1(power),
        apparentPower: round1(apparentPower),
        reactivePower: round1(reactivePower),
        energy: round1(cumulativeEnergy),
        energyReactive: round1(cumulativeReactive),
        energyApparent: round1(cumulativeApparent),
        voltage: 398 + rand() * 5,
        current: 0,
        frequency: round2(50 + (rand() - 0.5) * 0.06),
      });
    }
  } else if (days <= 60) {
    for (let t = from.getTime(); t <= to.getTime(); t += 86400_000) {
      const d = new Date(t);
      const power = 300 * (0.85 + rand() * 0.3);
      const pf = 0.88 + rand() * 0.07;
      const apparentPower = power / pf;
      const reactivePower = reactiveFromPF(power, pf);

      cumulativeEnergy += power * 24;
      cumulativeReactive += reactivePower * 24;
      cumulativeApparent += apparentPower * 24;

      points.push({
        timestamp: d.toISOString(),
        label: `${d.getDate()}/${d.getMonth() + 1}`,
        power: round1(power),
        apparentPower: round1(apparentPower),
        reactivePower: round1(reactivePower),
        energy: round1(cumulativeEnergy),
        energyReactive: round1(cumulativeReactive),
        energyApparent: round1(cumulativeApparent),
        voltage: 400,
        current: 0,
        frequency: round2(50 + (rand() - 0.5) * 0.06),
      });
    }
  } else {
    for (let t = from.getTime(); t <= to.getTime(); t += 7 * 86400_000) {
      const d = new Date(t);
      const power = 300 * (0.85 + rand() * 0.3);
      const pf = 0.88 + rand() * 0.07;
      const apparentPower = power / pf;
      const reactivePower = reactiveFromPF(power, pf);

      cumulativeEnergy += power * 24 * 7;
      cumulativeReactive += reactivePower * 24 * 7;
      cumulativeApparent += apparentPower * 24 * 7;

      points.push({
        timestamp: d.toISOString(),
        label: `${d.getDate()}/${d.getMonth() + 1}`,
        power: round1(power),
        apparentPower: round1(apparentPower),
        reactivePower: round1(reactivePower),
        energy: round1(cumulativeEnergy),
        energyReactive: round1(cumulativeReactive),
        energyApparent: round1(cumulativeApparent),
        voltage: 400,
        current: 0,
        frequency: round2(50 + (rand() - 0.5) * 0.06),
      });
    }
  }

  return points;
}

/**
 * Grouping meter per panel (Tempat).
 * Meter ber-role "outcoming" dihitung sebagai anak dari "incoming" pada panel
 * yang sama, jadi tidak dihitung dua kali dalam total daya panel.
 */
export function getPanels(): MeterPanel[] {
  const map = new Map<string, Device[]>();

  for (const d of DEVICES) {
    const list = map.get(d.location) ?? [];
    list.push(d);
    map.set(d.location, list);
  }

  return [...map.entries()].map(([location, devices]) => {
    const counted = devices.filter(
      (d) => d.role !== "outcoming" && d.status !== "offline",
    );
    return {
      location,
      brands: [...new Set(devices.map((d) => d.brand))],
      devices,
      power: round1(counted.reduce((s, d) => s + d.power, 0)),
      apparentPower: round1(counted.reduce((s, d) => s + d.apparentPower, 0)),
      reactivePower: round1(counted.reduce((s, d) => s + d.reactivePower, 0)),
      energyActive: round1(counted.reduce((s, d) => s + d.energyActive, 0)),
    };
  });
}

/** Data untuk grafik breakdown beban per panel */
export function getLoadByDevice() {
  return getPanels().map((p) => ({ name: p.location, power: p.power }));
}

/**
 * Total sistem.
 *
 * PENTING: total daya hanya menghitung meter ber-role "incoming"
 * (LVMDP Incoming + MVMDP). Meter "outcoming" dan "distribution" merupakan
 * pengukuran anak dari sumber tersebut, sehingga menghitung semuanya akan
 * menyebabkan double counting. Logika agregasi final akan dipindah ke backend.
 */
export function getTotals() {
  const sources = DEVICES.filter(
    (d) => d.role === "incoming" && d.status !== "offline",
  );
  const totalPower = round1(sources.reduce((s, d) => s + d.power, 0));
  const totalApparentPower = round1(
    sources.reduce((s, d) => s + d.apparentPower, 0),
  );
  const totalReactivePower = round1(
    sources.reduce((s, d) => s + d.reactivePower, 0),
  );
  const energyToday = round1(sources.reduce((s, d) => s + d.energyActive, 0));
  const energyReactiveToday = round1(
    sources.reduce((s, d) => s + d.energyReactive, 0),
  );
  const energyApparentToday = round1(
    sources.reduce((s, d) => s + d.energyApparent, 0),
  );

  const online = DEVICES.filter((d) => d.status === "online").length;
  const warning = DEVICES.filter((d) => d.status === "warning").length;
  const offline = DEVICES.filter((d) => d.status === "offline").length;

  return {
    totalPower,
    totalApparentPower,
    totalReactivePower,
    energyToday,
    energyReactiveToday,
    energyApparentToday,
    online,
    warning,
    offline,
    total: DEVICES.length,
  };
}

/** Meter yang punya data THD (untuk halaman Power Quality) */
export function getDevicesWithTHD() {
  return DEVICES.filter(
    (d) => d.status !== "offline" && d.thdCurrent !== null,
  );
}

/** Meter yang modelnya TIDAK mendukung THD sama sekali */
export function getDevicesWithoutTHDSupport() {
  return DEVICES.filter(
    (d) => !d.capabilities.thdCurrent || d.thdCurrent === null,
  );
}

export const ALARMS: Alarm[] = [
  {
    id: "ALM-101",
    timestamp: new Date(NOW.getTime() - 1000 * 60 * 8).toISOString(),
    deviceId: "PM-LVMDP-IN-03",
    deviceName: "LVMDP Incoming 3",
    severity: "warning",
    message: "Power factor turun di bawah 0.90 (PF = 0.88)",
    acknowledged: false,
  },
  {
    id: "ALM-102",
    timestamp: new Date(NOW.getTime() - 1000 * 60 * 42).toISOString(),
    deviceId: "PM-MCC4-01",
    deviceName: "MCC 4 Meter 1",
    severity: "critical",
    message: "Device offline - tidak ada heartbeat selama 42 menit",
    acknowledged: false,
  },
  {
    id: "ALM-103",
    timestamp: new Date(NOW.getTime() - 1000 * 60 * 60 * 3).toISOString(),
    deviceId: "PM-LVMDP-IN-01",
    deviceName: "LVMDP Incoming 1",
    severity: "info",
    message: "Beban melonjak melewati 100 kW",
    acknowledged: true,
  },
  {
    id: "ALM-104",
    timestamp: new Date(NOW.getTime() - 1000 * 60 * 21).toISOString(),
    deviceId: "PM-MVMDP-01",
    deviceName: "MVMDP",
    severity: "warning",
    message: "THD arus melebihi ambang 5% (THD-I = 5,8%)",
    acknowledged: false,
  },
  {
    id: "ALM-105",
    timestamp: new Date(NOW.getTime() - 1000 * 60 * 35).toISOString(),
    deviceId: "PM-LVMDP-IN-03",
    deviceName: "LVMDP Incoming 3",
    severity: "critical",
    message: "THD arus tinggi (THD-I = 6,2%) - periksa beban non-linear",
    acknowledged: false,
  },
];
