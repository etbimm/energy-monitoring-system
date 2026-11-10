"use client";

import Link from "next/link";
import { Settings2 } from "lucide-react";
import { useAuth } from "@/components/auth/auth-provider";
import { PageHeader } from "@/components/layout/page-header";
import { DeviceLocations } from "@/components/dashboard/device-locations";
import { DataState } from "@/components/ui/data-state";
import { DemoDataNotice } from "@/components/ui/demo-data-notice";
import { getPanelsForDevices } from "@/lib/device-data";
import { useEMSData } from "@/lib/use-ems-data";

export default function DevicesPage() {
  const { devices, loading, error, isDemo } = useEMSData();
  const { isAdmin } = useAuth();

  return (
    <>
      <PageHeader
        title="Devices"
        description="Daftar power meter terdaftar"
        action={
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-xs text-stone-500">
              Total {devices.length} power meter
            </span>
            {isAdmin ? (
              <Link
                href="/admin/devices"
                className="inline-flex items-center gap-1.5 rounded-lg bg-brand-700 px-3 py-2 text-xs font-semibold text-white shadow-sm hover:bg-brand-800"
              >
                <Settings2 className="h-4 w-4" aria-hidden />
                Kelola device
              </Link>
            ) : null}
          </div>
        }
      />
      {isDemo ? <DemoDataNotice /> : null}
      <DataState loading={loading} error={error} />
      <DeviceLocations panels={getPanelsForDevices(devices)} />
    </>
  );
}
