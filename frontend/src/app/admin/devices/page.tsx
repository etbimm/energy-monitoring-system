"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, Pencil, Plus, Power, PowerOff, Search } from "lucide-react";
import { AdminOnly } from "@/components/auth/admin-only";
import { PageHeader } from "@/components/layout/page-header";
import { Card } from "@/components/ui/card";
import { Alert, Button, Dialog, Field, errorMessage, inputClass } from "@/components/ui/form";
import {
  createDevice,
  listDeviceConfigs,
  listDeviceModels,
  listDeviceOptions,
  updateDevice,
  type DeviceConfig,
  type DeviceInput,
  type DeviceModelOption,
  type DeviceOptions,
  type Transport,
} from "@/lib/auth-api";
import { formatDateTime } from "@/lib/format";
const ROLE_LABEL: Record<string, string> = {
  incoming: "Incoming",
  outcoming: "Outcoming",
  distribution: "Distribution",
};

const TRANSPORT_LABEL: Record<string, string> = {
  rs485: "RS485 via gateway",
  ethernet: "Ethernet (Modbus TCP)",
};

/** Nilai select untuk opsi "Lainnya" (nilai baru yang diketik admin). */
const OTHER_MODEL = "__other__";
const OTHER = "__other__";

const EMPTY_OPTIONS: DeviceOptions = { customRoles: [], customTransports: [] };

/**
 * Select dengan pilihan bawaan, nilai "Lainnya" yang sudah pernah dipakai,
 * dan opsi "Lainnya..." untuk mengetik nilai baru.
 */
function ChoiceSelect({
  id,
  value,
  onChange,
  known,
  custom,
  customGroupLabel,
}: {
  id: string;
  value: string;
  onChange: (value: string) => void;
  known: Record<string, string>;
  custom: string[];
  customGroupLabel: string;
}) {
  // Nilai lama yang belum ada di daftar (mis. baru disimpan) tetap tampil.
  const extra = [...custom];
  if (value !== OTHER && !(value in known) && value && !extra.includes(value)) extra.push(value);
  return (
    <select id={id} value={value} onChange={(event) => onChange(event.target.value)} className={inputClass}>
      {Object.entries(known).map(([key, label]) => (
        <option key={key} value={key}>
          {label}
        </option>
      ))}
      {extra.length > 0 ? (
        <optgroup label={customGroupLabel}>
          {extra.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </optgroup>
      ) : null}
      <option value={OTHER}>Lainnya...</option>
    </select>
  );
}

interface FormState {
  deviceCode: string;
  name: string;
  location: string;
  /** Model terpilih dari daftar, atau OTHER_MODEL. */
  model: string;
  /** Nama model baru bila memilih "Lainnya". */
  customModel: string;
  /** Merek, wajib untuk model yang belum punya profil register. */
  brand: string;
  /** Peran terpilih, atau OTHER. */
  role: string;
  /** Peran baru bila memilih "Lainnya". */
  customRole: string;
  /** Jalur terpilih, atau OTHER. */
  transport: Transport;
  /** Jalur baru bila memilih "Lainnya". */
  customTransport: string;
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
    customModel: "",
    brand: device && !device.profileSupported ? (device.brand ?? "") : "",
    role: device?.role ?? "distribution",
    customRole: "",
    transport: device?.transport ?? "rs485",
    customTransport: "",
    modbusHost: device?.modbusHost ?? "",
    modbusPort: String(device?.modbusPort ?? 502),
    modbusAddress: device?.modbusAddress != null ? String(device.modbusAddress) : "1",
    ratedPowerKw: device?.ratedPowerKw != null ? String(device.ratedPowerKw) : "",
  };
}

function effectiveModel(form: FormState): string {
  return form.model === OTHER_MODEL ? form.customModel.trim() : form.model;
}

function effectiveRole(form: FormState): string {
  return form.role === OTHER ? form.customRole.trim() : form.role;
}

function effectiveTransport(form: FormState): string {
  return form.transport === OTHER ? form.customTransport.trim() : form.transport;
}

function toInput(form: FormState, supported: boolean): DeviceInput {
  return {
    name: form.name.trim(),
    location: form.location.trim() || null,
    model: effectiveModel(form),
    // Merek hanya dikirim untuk model "Lainnya"; model dikenal pakai katalog.
    brand: supported ? undefined : form.brand.trim(),
    role: effectiveRole(form),
    transport: effectiveTransport(form),
    modbusHost: form.modbusHost.trim(),
    modbusPort: Number(form.modbusPort),
    modbusAddress: Number(form.modbusAddress),
    ratedPowerKw: form.ratedPowerKw.trim() ? Number(form.ratedPowerKw) : null,
  };
}

function DeviceForm({
  device,
  models,
  options,
  onSaved,
  onCancel,
}: {
  device?: DeviceConfig;
  models: DeviceModelOption[];
  options: DeviceOptions;
  onSaved: (device: DeviceConfig) => void;
  onCancel: () => void;
}) {
  const [form, setForm] = useState<FormState>(() => toForm(device, models[0]?.model));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const selectedModel = models.find((item) => item.model === form.model);
  const isOther = form.model === OTHER_MODEL;
  // false untuk model "Lainnya" baru maupun model lain yang sudah pernah dipakai.
  const supported = !isOther && (selectedModel?.supported ?? true);
  const supportedModels = models.filter((item) => item.supported);
  const customModels = models.filter((item) => !item.supported);
  const set = <K extends keyof FormState>(key: K, value: FormState[K]) =>
    setForm((current) => ({ ...current, [key]: value }));

  function chooseModel(value: string) {
    const option = models.find((item) => item.model === value);
    setForm((current) => ({
      ...current,
      model: value,
      // Model lain yang sudah pernah dipakai: isi merek yang tersimpan.
      brand: option && !option.supported ? option.brand : value === OTHER_MODEL ? current.brand : "",
    }));
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isOther && !form.customModel.trim()) {
      setError("Nama model wajib diisi untuk pilihan Lainnya.");
      return;
    }
    if (!supported && !form.brand.trim()) {
      setError("Merek wajib diisi untuk model di luar daftar.");
      return;
    }
    if (form.role === OTHER && !form.customRole.trim()) {
      setError("Peran wajib diisi untuk pilihan Lainnya.");
      return;
    }
    if (form.transport === OTHER && !form.customTransport.trim()) {
      setError("Jalur wajib diisi untuk pilihan Lainnya.");
      return;
    }
    if (device && device.model !== effectiveModel(form)) {
      const ok = window.confirm(
        "Model diganti: peta register Modbus dan kapabilitas meter ikut berubah. Pastikan model sesuai alat di lapangan. Lanjutkan?",
      );
      if (!ok) return;
    }
    setSaving(true);
    setError(null);
    try {
      const input = toInput(form, supported);
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
        <Field
          label="Peran"
          htmlFor="dev-role"
          hint={
            form.role === "incoming"
              ? "Incoming dihitung ke total daya & energi pabrik."
              : "Hanya Incoming yang dihitung ke total daya & energi pabrik."
          }
        >
          <ChoiceSelect
            id="dev-role"
            value={form.role}
            onChange={(value) => set("role", value)}
            known={ROLE_LABEL}
            custom={options.customRoles}
            customGroupLabel="Peran lain yang pernah dipakai"
          />
        </Field>
        {form.role === OTHER ? (
          <Field label="Peran lainnya" htmlFor="dev-custom-role" hint="mis. Genset, Solar PV, Feeder">
            <input
              id="dev-custom-role"
              value={form.customRole}
              required
              maxLength={40}
              onChange={(event) => set("customRole", event.target.value)}
              className={inputClass}
            />
          </Field>
        ) : null}
        <Field
          label="Model meter"
          htmlFor="dev-model"
          hint={
            supported && selectedModel
              ? `${selectedModel.brand} · harmonik s/d orde ${selectedModel.capabilities.maxHarmonicOrder}`
              : undefined
          }
        >
          <select
            id="dev-model"
            value={form.model}
            required
            onChange={(event) => chooseModel(event.target.value)}
            className={inputClass}
          >
            <optgroup label="Didukung akuisisi">
              {supportedModels.map((item) => (
                <option key={item.model} value={item.model}>
                  {item.label}
                </option>
              ))}
            </optgroup>
            {customModels.length > 0 ? (
              <optgroup label="Model lain (belum ada profil register)">
                {customModels.map((item) => (
                  <option key={item.model} value={item.model}>
                    {item.label}
                  </option>
                ))}
              </optgroup>
            ) : null}
            <option value={OTHER_MODEL}>Lainnya (model/merek baru)...</option>
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
        {!supported ? (
          <>
            <Field label="Merek" htmlFor="dev-brand" hint="mis. Schneider Electric">
              <input
                id="dev-brand"
                value={form.brand}
                required
                maxLength={60}
                onChange={(event) => set("brand", event.target.value)}
                className={inputClass}
              />
            </Field>
            {isOther ? (
              <Field label="Nama model" htmlFor="dev-custom-model" hint="mis. PM5350">
                <input
                  id="dev-custom-model"
                  value={form.customModel}
                  required
                  maxLength={60}
                  onChange={(event) => set("customModel", event.target.value)}
                  className={inputClass}
                />
              </Field>
            ) : null}
            <p className="flex gap-2 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-900 sm:col-span-2">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
              <span>
                Model ini belum punya peta register Modbus, jadi datanya <strong>belum bisa dibaca</strong> dan
                device akan tampil offline. Agar terbaca, tambahkan profil register model ini di backend
                (<code>backend/app/acquisition/profiles.py</code>) dengan nama model yang sama persis.
              </span>
            </p>
          </>
        ) : null}
      </fieldset>

      <fieldset className="grid gap-3 sm:grid-cols-2">
        <legend className="mb-2 text-xs font-bold uppercase tracking-wider text-brand-700">Koneksi Modbus</legend>
        <Field
          label="Jalur"
          htmlFor="dev-transport"
          hint={
            form.transport in TRANSPORT_LABEL
              ? undefined
              : "Hanya informasi: akuisisi tetap membaca lewat Modbus TCP ke Host:Port."
          }
        >
          <ChoiceSelect
            id="dev-transport"
            value={form.transport}
            onChange={(value) => set("transport", value)}
            known={TRANSPORT_LABEL}
            custom={options.customTransports}
            customGroupLabel="Jalur lain yang pernah dipakai"
          />
        </Field>
        {form.transport === OTHER ? (
          <Field label="Jalur lainnya" htmlFor="dev-custom-transport" hint="mis. Modbus RTU via USB, Fiber optik">
            <input
              id="dev-custom-transport"
              value={form.customTransport}
              required
              maxLength={40}
              onChange={(event) => set("customTransport", event.target.value)}
              className={inputClass}
            />
          </Field>
        ) : null}
        <Field
          label="Host / IP"
          htmlFor="dev-host"
          hint={
            form.transport === "rs485"
              ? "IP gateway RS485-to-Ethernet."
              : form.transport === "ethernet"
                ? "IP power meter."
                : "IP power meter atau gateway Modbus TCP."
          }
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
  const [options, setOptions] = useState<DeviceOptions>(EMPTY_OPTIONS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [showInactive, setShowInactive] = useState(true);
  const [editing, setEditing] = useState<DeviceConfig | "new" | null>(null);
  const [pendingId, setPendingId] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [nextDevices, nextModels, nextOptions] = await Promise.all([
        listDeviceConfigs(),
        listDeviceModels(),
        listDeviceOptions(),
      ]);
      setDevices(nextDevices);
      setModels(nextModels);
      setOptions(nextOptions);
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
                    <td className="px-4 py-3 text-xs">
                      {modelLabel[device.model] ?? device.model}
                      {!device.profileSupported ? (
                        <span
                          title="Belum ada profil register: data tidak bisa dibaca akuisisi mode modbus"
                          className="mt-1 flex w-fit items-center gap-1 rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold text-amber-800"
                        >
                          <AlertTriangle className="h-3 w-3" aria-hidden />
                          Belum didukung
                        </span>
                      ) : null}
                    </td>
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
            options={options}
            onCancel={() => setEditing(null)}
            onSaved={(saved) => {
              upsert(saved);
              // Muat ulang agar model/peran/jalur "Lainnya" baru muncul di pilihan.
              void refresh();
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
