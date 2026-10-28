"use client";

import { PageHeader } from "@/components/layout/page-header";
import { DeviceLocations } from "@/components/dashboard/device-locations";
import { DataState } from "@/components/ui/data-state";
import { getPanelsForDevices } from "@/lib/device-data";
import { useEMSData } from "@/lib/use-ems-data";

export default function DevicesPage() {
  const { devices, loading, error } = useEMSData();

  return (
    <>
      <PageHeader
        title="Devices"
        description="Daftar power meter terdaftar"
        action={
          <span className="text-xs text-stone-500">
            Total {devices.length} power meter
          </span>
        }
      />

      <DataState loading={loading} error={error} />
      <DeviceLocations panels={getPanelsForDevices(devices)} />
    </>
  );
}
