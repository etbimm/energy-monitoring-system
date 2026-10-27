import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { ALARMS } from "@/lib/mock-data";
import { formatDateTime } from "@/lib/format";

const severityStyles = {
  critical: "border-brand-900 bg-brand-900 text-white",
  warning: "border-amber-300 bg-amber-50 text-amber-900",
  info: "border-stone-200 bg-stone-50 text-stone-700",
};

const severityLabel = {
  critical: "Kritis",
  warning: "Peringatan",
  info: "Info",
};

export default function AlarmsPage() {
  return (
    <>
      <PageHeader title="Alarms" description="Riwayat dan status alarm sistem" />

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-1">
        {ALARMS.map((alarm) => (
          <Card key={alarm.id} className={`min-w-0 border p-3 sm:p-4 ${severityStyles[alarm.severity]}`}>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-sm font-medium">{alarm.message}</p>
                <p className="mt-1 text-xs opacity-75">
                  {alarm.deviceName} ({alarm.deviceId}) -{" "}
                  {formatDateTime(alarm.timestamp)}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <span className="rounded-full bg-white/20 px-2.5 py-0.5 text-[11px] uppercase tracking-wider">
                  {severityLabel[alarm.severity]}
                </span>
                <span className="text-[11px] uppercase tracking-wider opacity-80">
                  {alarm.acknowledged ? "Acknowledged" : "Baru"}
                </span>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </>
  );
}
