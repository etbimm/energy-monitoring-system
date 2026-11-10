"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Pencil, Plus, Power, PowerOff, Search } from "lucide-react";
import { AdminOnly } from "@/components/auth/admin-only";
import { PageHeader } from "@/components/layout/page-header";
import { Card } from "@/components/ui/card";
import { Alert, Button, Dialog, Field, errorMessage, inputClass } from "@/components/ui/form";
import {
  createDevice,
  listDeviceConfigs,
  listDeviceModels,
  updateDevice,
  type DeviceConfig,
  type DeviceInput,
  type DeviceModelOption,
  type Transport,
} from "@/lib/auth-api";
import { formatDateTime } from "@/lib/format";
import type { MeterRole } from "@/lib/types";

const ROLE_LABEL: Record<MeterRole, string> = {
  incoming: "Incoming",
  outcoming: "Outcoming",
  distribution: "Distribution",
};

const TRANSPORT_LABEL: Record<Transport, string> = {
  rs485: "RS485 via gateway",
  ethernet: "Ethernet (Modbus TCP)",
};

interface FormState {
  deviceCode: string;
  name: string;
  location: string;
  model: string;
  role: MeterRole;
  transport: Transport;
  modbusHost: string;
  modbusPort: string;
  modbusAddress: string;
  ratedPowerKw: string;
}

function toForm(device?: DeviceConfig, defaultModel = ""): FormState {
  return {
    deviceCode: device?.id ?? "PM-",
    name: device?.name ?? "",
    location: device?.location ?? "",
    model: device?.model ?? defaultModel,
    role: device?.role ?? "distribution",
    transport: device?.transport ?? "rs485",
    modbusHost: device?.modbusHost ?? "",
    modbusPort: String(device?.modbusPort ?? 502),
    modbusAddress: device?.modbusAddress != null ? String(device.modbusAddress) : "1",
    ratedPowerKw: device?.ratedPowerKw != null ? String(device.ratedPowerKw) : "",
  };
}

function toInput(form: FormState): DeviceInput {
  return {
    name: form.name.trim(),
    location: form.location.trim() || null,
    model: form.model,
    role: form.role,
    transport: form.transport,
    modbusHost: form.modbusHost.trim(),
    modbusPort: Number(form.modbusPort),
    modbusAddress: Number(form.modbusAddress),
    ratedPowerKw: form.ratedPowerKw.trim() ? Number(form.ratedPowerKw) : null,
  };
}

function DeviceForm({
  device,
  models,
  onSaved,
  onCancel,
}: {
  device?: DeviceConfig;
  models: DeviceModelOption[];
  onSaved: (device: DeviceConfig) => void;
  onCancel: () => void;
}) {
  const [form, setForm] = useState<FormState>(() => toForm(device, models[0]?.model));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const selectedModel = models.find((item) => item.model === form.model);
  const set = <K extends keyof FormState>(key: K, value: FormState[K]) =>
    setForm((current) => ({ ...current, [key]: value }));

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (device && device.model !== form.model) {
      const ok = window.confirm(
        "Model diganti: peta register Modbus dan kapabilitas meter ikut berubah. Pastikan model sesuai alat di lapangan. Lanjutkan?",
      );
      if (!ok) return;
    }
    setSaving(true);
    setError(null);
    try {
      const input = toInput(form);
      const saved = device
        ? await updateDevice(device.id, input)
        : await createDevice({ ...input, deviceCode: form.deviceCode.trim().toUpperCase() });
      onSaved(saved);
    } catch (cause) {
      setError(errorMessage(cause, "Gagal menyimpan device."));
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error ? <Alert>{error}</Alert> : null}

      <fieldset className="grid gap-3 sm:grid-cols-2">
        <legend className="mb-2 text-xs font-bold uppercase tracking-wider text-brand-700">Identitas</legend>
        <Field
          label="Kode device"
          htmlFor="dev-code"
          hint={device ? "Kode tidak bisa diubah (dipakai di data & alarm)." : "Format PM-LOKASI-NN, mis. PM-MCC5-01"}
        >
          <input
            id="dev-code"
            value={form.deviceCode}
            disabled={Boolean(device)}
            required
            maxLength={40}
            onChange={(event) => set("deviceCode", event.target.value.toUpperCase())}
            className={`${inputClass} font-mono`}
          />
        </Field>
        <Field label="Nama" htmlFor="dev-name">
          <input
            id="dev-name"
            value={form.name}
            required
            maxLength={80}
            onChange={(event) => set("name", event.target.value)}
            className={inputClass}
          />
        </Field>
        <Field label="Lokasi / panel" htmlFor="dev-location">
          <input
            id="dev-location"
            value={form.location}
            maxLength={80}
            placeholder="mis. MCC 5"
            onChange={(event) => set("location", event.target.value)}
            className={inputClass}
          />
        </Field>
        <Field label="Peran" htmlFor="dev-role" hint="Incoming dipakai untuk total daya & energi pabrik.">
          <select
            id="dev-role"
            value={form.role}
            onChange={(event) => set("role", event.target.value as MeterRole)}
            className={inputClass}
          >
            {Object.entries(ROLE_LABEL).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </Field>
        <Field
          label="Model meter"
          htmlFor="dev-model"
          hint={selectedModel ? `${selectedModel.brand} · harmonik s/d orde ${selectedModel.capabilities.maxHarmonicOrder}` : undefined}
        >
          <select
            id="dev-model"
            value={form.model}
            required
            onChange={(event) => set("model", event.target.value)}
            className={inputClass}
          >
            {models.map((item) => (
              <option key={item.model} value={item.model}>
                {item.label}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Daya rating (kW)" htmlFor="dev-rated" hint="Opsional. Dipakai untuk alarm beban lebih.">
          <input
            id="dev-rated"
            type="number"
            min="0"
            step="any"
            value={form.ratedPowerKw}
            onChange={(event) => set("ratedPowerKw", event.target.value)}
            className={inputClass}
          />
        </Field>
      </fieldset>

      <fieldset className="grid gap-3 sm:grid-cols-2">
        <legend className="mb-2 text-xs font-bold uppercase tracking-wider text-brand-700">Koneksi Modbus</legend>
        <Field label="Jalur" htmlFor="dev-transport">
          <select
            id="dev-transport"
            value={form.transport}
            onChange={(event) => set("transport", event.target.value as Transport)}
            className={inputClass}
          >
            {Object.entries(TRANSPORT_LABEL).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </Field>
        <Field
          label="Host / IP"
          htmlFor="dev-host"
          hint={form.transport === "rs485" ? "IP gateway RS485-to-Ethernet." : "IP power meter."}
        >
          <input
            id="dev-host"
            value={form.modbusHost}
            required
            placeholder="192.168.10.30"
            onChange={(event) => set("modbusHost", event.target.value)}
            className={`${inputClass} font-mono`}
          />
        </Field>
        <Field label="Port" htmlFor="dev-port">
          <input
            id="dev-port"
            type="number"
            min="1"
            max="65535"
            required
            value={form.modbusPort}
            onChange={(event) => set("modbusPort", event.target.value)}
            className={inputClass}
          />
        </Field>
        <Field label="Slave ID (unit)" htmlFor="dev-address" hint="1-247. Harus unik per gateway.">
          <input
            id="dev-address"
            type="number"
            min="1"
            max="247"
            required
            value={form.modbusAddress}
            onChange={(event) => set("modbusAddress", event.target.value)}
            className={inputClass}
          />
        </Field>
      </fieldset>

      <p className="rounded-lg bg-stone-50 px-3 py-2 text-xs text-stone-600">
        Perubahan dibaca layanan akuisisi paling lambat 60 detik setelah disimpan.
      </p>

      <div className="flex justify-end gap-2">
        <Button variant="secondary" onClick={onCancel}>
          Batal
        </Button>
        <Button type="submit" disabled={saving || models.length === 0}>
          {saving ? "Menyimpan..." : device ? "Simpan perubahan" : "Tambah device"}
        </Button>
      </div>
    </form>
  );
}

function DevicesManager() {
  const [devices, setDevices] = useState<DeviceConfig[]>([]);
  const [models, setModels] = useState<DeviceModelOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [showInactive, setShowInactive] = useState(true);
  const [editing, setEditing] = useState<DeviceConfig | "new" | null>(null);
  const [pendingId, setPendingId] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [nextDevices, nextModels] = await Promise.all([listDeviceConfigs(), listDeviceModels()]);
      setDevices(nextDevices);
      setModels(nextModels);
      setError(null);
    } catch (cause) {
      setError(errorMessage(cause, "Gagal memuat daftar device."));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const modelLabel = useMemo(
    () => Object.fromEntries(models.map((item) => [item.model, item.label])),
    [models],
  );

  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return devices.filter((device) => {
      if (!showInactive && !device.isActive) return false;
      if (!needle) return true;
      return [device.id, device.name, device.location, device.model, device.modbusHost]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(needle));
    });
  }, [devices, query, showInactive]);

  const activeCount = devices.filter((device) => device.isActive).length;

  function upsert(saved: DeviceConfig) {
    setDevices((current) =>
      current.some((item) => item.id === saved.id)
        ? current.map((item) => (item.id === saved.id ? saved : item))
        : [...current, saved],
    );
  }

  async function toggleActive(device: DeviceConfig) {
    const message = device.isActive
      ? `Nonaktifkan ${device.id} (${device.name})?\n\nMeter tidak lagi dibaca dan tidak tampil di dashboard. Alarm aktifnya ditutup. Data riwayat TETAP tersimpan dan meter bisa diaktifkan kembali.`
      : `Aktifkan kembali ${device.id} (${device.name})?`;
    if (!window.confirm(message)) return;
    setPendingId(device.id);
    setNotice(null);
    try {
      const saved = await updateDevice(device.id, { isActive: !device.isActive });
      upsert(saved);
      setNotice(`${saved.id} ${saved.isActive ? "diaktifkan" : "dinonaktifkan"}.`);
      setError(null);
    } catch (cause) {
      setError(errorMessage(cause, "Gagal mengubah status device."));
    } finally {
      setPendingId(null);
    }
  }

  return (
    <>
      <PageHeader
        title="Kelola Device"
        description={`${activeCount} aktif dari ${devices.length} power meter terdaftar`}
        action={
          <Button onClick={() => setEditing("new")} disabled={models.length === 0}>
            <Plus className="h-4 w-4" aria-hidden />
            Tambah device
          </Button>
        }
      />

      <div className="mb-4 space-y-2">
        {error ? <Alert>{error}</Alert> : null}
        {notice ? <Alert tone="success">{notice}</Alert> : null}
      </div>

      <Card className="overflow-hidden">
        <div className="flex flex-wrap items-center gap-3 border-b border-stone-200 px-4 py-3">
          <label className="relative min-w-0 flex-1 sm:max-w-xs">
            <span className="sr-only">Cari device</span>
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-400" aria-hidden />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Cari kode, nama, lokasi, IP..."
              className={`${inputClass} pl-9`}
            />
          </label>
          <label className="flex items-center gap-2 text-xs text-stone-600">
            <input
              type="checkbox"
              checked={showInactive}
              onChange={(event) => setShowInactive(event.target.checked)}
              className="h-4 w-4 accent-brand-700"
            />
            Tampilkan device nonaktif
          </label>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[900px] text-left text-sm">
            <thead className="bg-stone-50 text-xs uppercase tracking-wide text-stone-500">
              <tr>
                <th className="px-4 py-3">Kode</th>
                <th className="px-4 py-3">Nama / Lokasi</th>
                <th className="px-4 py-3">Model</th>
                <th className="px-4 py-3">Peran</th>
                <th className="px-4 py-3">Modbus</th>
                <th className="px-4 py-3">Data terakhir</th>
                <th className="px-4 py-3 text-right">Aksi</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {loading ? (
                <tr>
                  <td colSpan={7} className="px-4 py-6 text-center text-stone-500">
                    Memuat...
                  </td>
                </tr>
              ) : visible.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-6 text-center text-stone-500">
                    Tidak ada device yang cocok.
                  </td>
                </tr>
              ) : (
                visible.map((device) => (
                  <tr key={device.id} className={device.isActive ? "" : "bg-stone-50 text-stone-500"}>
                    <td className="px-4 py-3">
                      <p className="font-mono text-xs font-semibold">{device.id}</p>
                      {!device.isActive ? (
                        <span className="mt-1 inline-block rounded bg-stone-200 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-stone-600">
                          Nonaktif
                        </span>
                      ) : null}
                    </td>
                    <td className="px-4 py-3">
                      <p className="font-medium">{device.name}</p>
                      <p className="text-xs text-stone-500">{device.location ?? "-"}</p>
                    </td>
                    <td className="px-4 py-3 text-xs">{modelLabel[device.model] ?? device.model}</td>
                    <td className="px-4 py-3 text-xs">{ROLE_LABEL[device.role] ?? device.role}</td>
                    <td className="px-4 py-3 font-mono text-xs">
                      {device.modbusHost ?? "-"}:{device.modbusPort}
                      <span className="text-stone-500"> #{device.modbusAddress ?? "-"}</span>
                      <p className="font-sans text-[11px] text-stone-500">
                        {device.transport ? TRANSPORT_LABEL[device.transport] : "-"}
                      </p>
                    </td>
                    <td className="px-4 py-3 text-xs">
                      {device.lastSeen ? formatDateTime(device.lastSeen) : "Belum ada data"}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex justify-end gap-1.5">
                        <Button variant="secondary" onClick={() => setEditing(device)}>
                          <Pencil className="h-3.5 w-3.5" aria-hidden />
                          Edit
                        </Button>
                        <Button
                          variant={device.isActive ? "danger" : "success"}
                          disabled={pendingId === device.id}
                          onClick={() => void toggleActive(device)}
                        >
                          {device.isActive ? (
                            <PowerOff className="h-3.5 w-3.5" aria-hidden />
                          ) : (
                            <Power className="h-3.5 w-3.5" aria-hidden />
                          )}
                          {device.isActive ? "Nonaktifkan" : "Aktifkan"}
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>

      <Dialog
        open={editing !== null}
        wide
        title={editing === "new" ? "Tambah device" : `Edit ${editing?.id ?? ""}`}
        onClose={() => setEditing(null)}
      >
        {editing !== null ? (
          <DeviceForm
            key={editing === "new" ? "new" : editing.id}
            device={editing === "new" ? undefined : editing}
            models={models}
            onCancel={() => setEditing(null)}
            onSaved={(saved) => {
              upsert(saved);
              setNotice(editing === "new" ? `${saved.id} berhasil ditambahkan.` : `${saved.id} diperbarui.`);
              setEditing(null);
            }}
          />
        ) : null}
      </Dialog>
    </>
  );
}

export default function AdminDevicesPage() {
  return (
    <AdminOnly>
      <DevicesManager />
    </AdminOnly>
  );
}
