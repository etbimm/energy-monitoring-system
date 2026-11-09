import type {
  Alarm,
  Device,
  PhaseReading,
  TimeSeriesPoint,
} from "@/lib/types";
import { PLANT_TIME_ZONE } from "@/lib/time";

export interface Summary {
  totalPower: number;
  totalApparentPower: number;
  totalReactivePower: number;
  energyToday: number;
  online: number;
  warning: number;
  offline: number;
  total: number;
}

type NullableKeys =
  | "voltage"
  | "current"
  | "power"
  | "apparentPower"
  | "reactivePower"
  | "energyActive"
  | "energyReactive"
  | "powerFactor"
  | "energyApparent"
  | "thdCurrent"
  | "thdVoltage"
  | "unbalanceVoltage"
  | "unbalanceCurrent"
  | "frequency";

type DeviceResponse = Omit<
  Device,
  NullableKeys | "lastSeen" | "phases" | "location" | "brand"
> & {
  [key in NullableKeys]: number | null;
} & {
  location: string | null;
  brand: string | null;
  lastSeen: string | null;
  phases: Array<
    Omit<PhaseReading, "voltage" | "current" | "power" | "apparentPower" | "reactivePower" | "powerFactor" | "thdCurrent" | "thdVoltage"> &
      Partial<
        Record<
          "voltage" | "current" | "power" | "apparentPower" | "reactivePower" | "powerFactor" | "thdCurrent" | "thdVoltage",
          number | null
        >
      >
  >;
};

type ReadingResponse = Omit<
  TimeSeriesPoint,
  | "power"
  | "apparentPower"
  | "reactivePower"
  | "energy"
  | "energyReactive"
  | "energyApparent"
  | "voltage"
  | "current"
  | "frequency"
  | "powerFactor"
  | "thdCurrent"
> & {
  [key in
    | "power"
    | "apparentPower"
    | "reactivePower"
    | "energy"
    | "energyReactive"
    | "energyApparent"
    | "voltage"
    | "current"
    | "frequency"
    | "powerFactor"
    | "thdCurrent"]: number | null;
};

const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:4000").replace(
  /\/$/,
  "",
);
const activeClientErrors = new Set<string>();

function clientErrorKey(path: string, method: string): string {
  const route = path.split("?")[0].replace(/[^a-zA-Z0-9._-]/g, "-");
  return `network-${method.toLowerCase()}-${route}`.slice(0, 120);
}

async function reportClientNetworkError(key: string, path: string): Promise<void> {
  if (activeClientErrors.has(key)) return;
  activeClientErrors.add(key);
  try {
    const response = await fetch(`${API_URL}/api/client-errors`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        key,
        summary: `Tidak dapat menghubungi ${path.split("?")[0]}`,
      }),
      cache: "no-store",
    });
    if (!response.ok) activeClientErrors.delete(key);
  } catch {
    console.error(`EMS API tidak dapat dihubungi: ${path.split("?")[0]}`);
  }
}

async function resolveClientNetworkError(key: string): Promise<void> {
  if (!activeClientErrors.has(key)) return;
  try {
    const response = await fetch(
      `${API_URL}/api/client-errors/${encodeURIComponent(key)}/resolve`,
      { method: "POST", cache: "no-store" },
    );
    if (response.ok) activeClientErrors.delete(key);
  } catch {
    // Keep the incident active so the next successful API request can resolve it.
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  const method = init?.method ?? "GET";
  const clientError = clientErrorKey(path, method);
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
      cache: "no-store",
    });
  } catch (error) {
    void reportClientNetworkError(clientError, path);
    throw new Error(
      `Backend tidak dapat dihubungi: ${error instanceof Error ? error.message : "kesalahan jaringan"}`,
    );
  }
  void resolveClientNetworkError(clientError);

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail =
      typeof body === "object" && body !== null && "detail" in body
        ? String(body.detail)
        : response.statusText;
    throw new Error(`API ${response.status}: ${detail}`);
  }
  return response.json();
}

function mapDevice(device: DeviceResponse): Device {
  // Nilai yang tidak tersedia tetap null (ditampilkan "–"), bukan 0.
  const orNull = (value: number | null | undefined) => value ?? null;
  return {
    ...device,
    location: device.location ?? "Tidak diketahui",
    brand: device.brand ?? "Tidak diketahui",
    lastSeen: device.lastSeen ?? "",
    voltage: orNull(device.voltage),
    current: orNull(device.current),
    power: orNull(device.power),
    apparentPower: orNull(device.apparentPower),
    reactivePower: orNull(device.reactivePower),
    energyActive: orNull(device.energyActive),
    energyReactive: orNull(device.energyReactive),
    powerFactor: orNull(device.powerFactor),
    energyApparent: orNull(device.energyApparent),
    thdCurrent: device.thdCurrent,
    thdVoltage: device.thdVoltage,
    unbalanceVoltage: device.unbalanceVoltage,
    unbalanceCurrent: device.unbalanceCurrent,
    frequency: orNull(device.frequency),
    phases: device.phases.map((phase) => ({
      phase: phase.phase,
      voltage: phase.voltage ?? null,
      current: phase.current ?? null,
      power: phase.power ?? null,
      apparentPower: phase.apparentPower ?? null,
      reactivePower: phase.reactivePower ?? null,
      powerFactor: phase.powerFactor ?? null,
      thdCurrent: phase.thdCurrent ?? null,
      thdVoltage: phase.thdVoltage ?? null,
    })),
  };
}

export async function getDevices(): Promise<Device[]> {
  const devices = await request<DeviceResponse[]>("/api/devices");
  return devices.map(mapDevice);
}

export function getSummary(): Promise<Summary> {
  return request("/api/summary/today");
}

export async function getReadings({
  from,
  to,
  bucket = "5m",
  device,
}: {
  from: string;
  to: string;
  bucket?: "raw" | "1m" | "5m" | "15m" | "1h" | "1d";
  device?: string;
}): Promise<TimeSeriesPoint[]> {
  const params = new URLSearchParams({ from, to, bucket });
  if (device) params.set("device", device);
  const rows = await request<ReadingResponse[]>(`/api/readings?${params}`);
  return rows.map((row) => ({
    ...row,
    power: row.power ?? null,
    apparentPower: row.apparentPower ?? null,
    reactivePower: row.reactivePower ?? null,
    energy: row.energy ?? null,
    energyReactive: row.energyReactive ?? null,
    energyApparent: row.energyApparent ?? null,
    voltage: row.voltage ?? null,
    current: row.current ?? null,
    frequency: row.frequency ?? null,
    powerFactor: row.powerFactor ?? null,
    thdCurrent: row.thdCurrent,
    label: row.label || new Date(row.timestamp).toLocaleTimeString("id-ID", {
      timeZone: PLANT_TIME_ZONE,
      hour: "2-digit",
      minute: "2-digit",
    }),
  }));
}

export interface EnergyTotals {
  energyActive: number;
  energyReactive: number;
  energyApparent: number;
  devices: number;
}

export function getEnergyTotals({
  from,
  to,
  device,
}: {
  from: string;
  to: string;
  device?: string;
}): Promise<EnergyTotals> {
  const params = new URLSearchParams({ from, to });
  if (device) params.set("device", device);
  return request(`/api/energy?${params}`);
}

export function getAlarms(includeCleared = false): Promise<Alarm[]> {
  return request(`/api/alarms?include_cleared=${includeCleared}`);
}

export function acknowledgeAlarm(id: string): Promise<Alarm> {
  if (!/^\d+$/.test(id)) {
    throw new Error("ID alarm tidak valid untuk acknowledge.");
  }
  return request(`/api/alarms/${id}/acknowledge`, { method: "POST" });
}

export function getRealtimeUrl(): string {
  const configured = process.env.NEXT_PUBLIC_WS_URL;
  if (configured) return configured;
  return `${API_URL.replace(/^http/, "ws")}/ws`;
}
