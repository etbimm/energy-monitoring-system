import type {
  Alarm,
  Device,
  PhaseReading,
  TimeSeriesPoint,
} from "@/lib/types";

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

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
      cache: "no-store",
    });
  } catch (error) {
    throw new Error(
      `Backend tidak dapat dihubungi: ${error instanceof Error ? error.message : "kesalahan jaringan"}`,
    );
  }

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
  const numberOrZero = (value: number | null | undefined) => value ?? 0;
  return {
    ...device,
    location: device.location ?? "Tidak diketahui",
    brand: device.brand ?? "Tidak diketahui",
    lastSeen: device.lastSeen ?? "",
    voltage: numberOrZero(device.voltage),
    current: numberOrZero(device.current),
    power: numberOrZero(device.power),
    apparentPower: numberOrZero(device.apparentPower),
    reactivePower: numberOrZero(device.reactivePower),
    energyActive: numberOrZero(device.energyActive),
    energyReactive: numberOrZero(device.energyReactive),
    powerFactor: numberOrZero(device.powerFactor),
    energyApparent: numberOrZero(device.energyApparent),
    thdCurrent: device.thdCurrent,
    thdVoltage: device.thdVoltage,
    unbalanceVoltage: device.unbalanceVoltage,
    unbalanceCurrent: device.unbalanceCurrent,
    frequency: numberOrZero(device.frequency),
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
  bucket?: "raw" | "1m" | "5m" | "15m" | "1h";
  device?: string;
}): Promise<TimeSeriesPoint[]> {
  const params = new URLSearchParams({ from, to, bucket });
  if (device) params.set("device", device);
  const rows = await request<ReadingResponse[]>(`/api/readings?${params}`);
  return rows.map((row) => ({
    ...row,
    power: row.power ?? 0,
    apparentPower: row.apparentPower ?? 0,
    reactivePower: row.reactivePower ?? 0,
    energy: row.energy ?? 0,
    energyReactive: row.energyReactive ?? 0,
    energyApparent: row.energyApparent ?? 0,
    voltage: row.voltage ?? 0,
    current: row.current ?? 0,
    frequency: row.frequency ?? 0,
    powerFactor: row.powerFactor ?? 0,
    thdCurrent: row.thdCurrent,
    label: row.label || new Date(row.timestamp).toLocaleTimeString("id-ID", {
      hour: "2-digit",
      minute: "2-digit",
    }),
  }));
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
