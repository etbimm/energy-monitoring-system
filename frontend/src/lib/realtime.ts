import type { Summary } from "@/lib/api";
import type { Device, PhaseReading } from "@/lib/types";

/** Payload telemetry dari WebSocket backend (snake_case, lihat ingest.py). */
export interface TelemetryMessage {
  device_code: string;
  timestamp?: string | null;
  status?: Device["status"];
  voltage?: number | null;
  current?: number | null;
  power?: number | null;
  apparent_power?: number | null;
  reactive_power?: number | null;
  energy_active?: number | null;
  energy_reactive?: number | null;
  energy_apparent?: number | null;
  power_factor?: number | null;
  frequency?: number | null;
  thd_current?: number | null;
  thd_voltage?: number | null;
  unbalance_voltage?: number | null;
  unbalance_current?: number | null;
  phases?: Record<string, Partial<Record<string, number | null>>> | null;
}

const PHASES = ["L1", "L2", "L3"] as const;

function num(value: number | null | undefined, fallback: number): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function phasesFrom(message: TelemetryMessage, previous: PhaseReading[]): PhaseReading[] {
  if (!message.phases) return previous;
  return PHASES.filter((phase) => message.phases?.[phase]).map((phase) => {
    const raw = message.phases?.[phase] ?? {};
    const pick = (key: string) => (typeof raw[key] === "number" ? (raw[key] as number) : null);
    return {
      phase,
      voltage: pick("voltage"),
      current: pick("current"),
      power: pick("power"),
      apparentPower: pick("apparent_power"),
      reactivePower: pick("reactive_power"),
      powerFactor: pick("power_factor"),
      thdCurrent: pick("thd_current"),
      thdVoltage: pick("thd_voltage"),
    };
  });
}

/**
 * Gabungkan satu pesan telemetry ke data device yang sudah dimuat dari REST.
 *
 * Status `warning` dari alarm hanya diketahui REST, jadi status tidak ditimpa
 * kecuali meter sebelumnya offline (data baru = meter kembali online).
 */
export function applyTelemetry(device: Device, message: TelemetryMessage): Device {
  return {
    ...device,
    status: device.status === "offline" ? "online" : device.status,
    lastSeen: message.timestamp ?? device.lastSeen,
    voltage: num(message.voltage, device.voltage),
    current: num(message.current, device.current),
    power: num(message.power, device.power),
    apparentPower: num(message.apparent_power, device.apparentPower),
    reactivePower: num(message.reactive_power, device.reactivePower),
    energyActive: num(message.energy_active, device.energyActive),
    energyReactive: num(message.energy_reactive, device.energyReactive),
    energyApparent: num(message.energy_apparent, device.energyApparent),
    powerFactor: num(message.power_factor, device.powerFactor),
    frequency: num(message.frequency, device.frequency),
    thdCurrent: message.thd_current ?? device.thdCurrent,
    thdVoltage: message.thd_voltage ?? device.thdVoltage,
    unbalanceVoltage: message.unbalance_voltage ?? device.unbalanceVoltage,
    unbalanceCurrent: message.unbalance_current ?? device.unbalanceCurrent,
    phases: phasesFrom(message, device.phases),
  };
}

/** Hitung ulang total daya (meter incoming) dari data device terbaru. */
export function withLiveTotals(summary: Summary, devices: Device[]): Summary {
  const incoming = devices.filter((device) => device.role === "incoming");
  const sum = (key: "power" | "apparentPower" | "reactivePower") =>
    incoming.reduce((total, device) => total + (device[key] ?? 0), 0);
  return {
    ...summary,
    totalPower: sum("power"),
    totalApparentPower: sum("apparentPower"),
    totalReactivePower: sum("reactivePower"),
  };
}
