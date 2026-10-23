import { PageHeader } from "@/components/layout/page-header";
import { DeviceTable, DeviceCards } from "@/components/dashboard/device-table";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { DEVICES, TOTAL_METERS } from "@/lib/mock-data";

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

      <Card>
        <CardHeader
          title="Semua Device"
          subtitle={`${DEVICES.length} device terdaftar`}
        />
        <CardContent>
          <DeviceCards devices={DEVICES} />
          <DeviceTable devices={DEVICES} />
        </CardContent>
      </Card>
    </>
  );
}
