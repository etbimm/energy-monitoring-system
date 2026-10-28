import type { Device, MeterPanel } from "@/lib/types";

export function getPanelsForDevices(devices: Device[]): MeterPanel[] {
  const grouped = new Map<string, Device[]>();
  for (const device of devices) {
    const panel = grouped.get(device.location) ?? [];
    panel.push(device);
    grouped.set(device.location, panel);
  }

  return [...grouped.entries()].map(([location, panelDevices]) => {
    const counted = panelDevices.filter(
      (device) => device.role !== "outcoming" && device.status !== "offline",
    );
    return {
      location,
      brands: [...new Set(panelDevices.map((device) => device.brand))],
      devices: panelDevices,
      power: counted.reduce((total, device) => total + device.power, 0),
      apparentPower: counted.reduce((total, device) => total + device.apparentPower, 0),
      reactivePower: counted.reduce((total, device) => total + device.reactivePower, 0),
      energyActive: counted.reduce((total, device) => total + device.energyActive, 0),
    };
  });
}

export function getLoadByPanel(devices: Device[]) {
  return getPanelsForDevices(devices).map((panel) => ({
    name: panel.location,
    power: panel.power,
  }));
}
