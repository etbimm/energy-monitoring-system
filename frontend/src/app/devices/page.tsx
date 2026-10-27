import { PageHeader } from "@/components/layout/page-header";
import { DeviceLocations } from "@/components/dashboard/device-locations";
import { getPanels, TOTAL_METERS } from "@/lib/mock-data";

export default function DevicesPage() {
  return (
    <>
      <PageHeader
        title="Devices"
        description="Daftar power meter terdaftar"
        action={
          <span className="text-xs text-stone-500">
            Total {TOTAL_METERS} power meter
          </span>
        }
      />

      <DeviceLocations panels={getPanels()} />
    </>
  );
}
