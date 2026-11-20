"use client";

import { useCallback, useEffect, useState } from "react";
import { RefreshCw, Save } from "lucide-react";
import { AdminOnly } from "@/components/auth/admin-only";
import { PageHeader } from "@/components/layout/page-header";
import { Card } from "@/components/ui/card";
import { Alert, Button, errorMessage, Field, inputClass } from "@/components/ui/form";
import {
  DEFAULT_ALARM_THRESHOLDS,
  getAlarmThresholds,
  updateAlarmThresholds,
  type AlarmThresholds,
} from "@/lib/auth-api";

interface ThresholdForm {
  voltageLlWarningLow: string;
  voltageLlWarningHigh: string;
  voltageLlCriticalLow: string;
  voltageLlCriticalHigh: string;
  powerFactorWarning: string;
  powerFactorCritical: string;
  frequencyWarning: string;
  frequencyCritical: string;
  thdCurrentWarning: string;
  thdCurrentCritical: string;
  unbalanceVoltageWarning: string;
  unbalanceVoltageCritical: string;
  /** Persen dari daya rating meter (mis. 80 = 80%). */
  loadWarning: string;
  loadCritical: string;
}

function toForm(thresholds: AlarmThresholds): ThresholdForm {
  return {
    voltageLlWarningLow: String(thresholds.voltageLlWarningLow),
    voltageLlWarningHigh: String(thresholds.voltageLlWarningHigh),
    voltageLlCriticalLow: String(thresholds.voltageLlCriticalLow),
    voltageLlCriticalHigh: String(thresholds.voltageLlCriticalHigh),
    powerFactorWarning: String(thresholds.powerFactorWarning),
    powerFactorCritical: String(thresholds.powerFactorCritical),
    frequencyWarning: String(thresholds.frequencyWarning),
    frequencyCritical: String(thresholds.frequencyCritical),
    thdCurrentWarning: String(thresholds.thdCurrentWarning),
    thdCurrentCritical: String(thresholds.thdCurrentCritical),
    unbalanceVoltageWarning: String(thresholds.unbalanceVoltageWarning),
    unbalanceVoltageCritical: String(thresholds.unbalanceVoltageCritical),
    loadWarning: String(Math.round(thresholds.loadWarning * 100)),
    loadCritical: String(Math.round(thresholds.loadCritical * 100)),
  };
}

function toPayload(form: ThresholdForm): AlarmThresholds {
  return {
    voltageLlWarningLow: Number(form.voltageLlWarningLow),
    voltageLlWarningHigh: Number(form.voltageLlWarningHigh),
    voltageLlCriticalLow: Number(form.voltageLlCriticalLow),
    voltageLlCriticalHigh: Number(form.voltageLlCriticalHigh),
    powerFactorWarning: Number(form.powerFactorWarning),
    powerFactorCritical: Number(form.powerFactorCritical),
    frequencyWarning: Number(form.frequencyWarning),
    frequencyCritical: Number(form.frequencyCritical),
    thdCurrentWarning: Number(form.thdCurrentWarning),
    thdCurrentCritical: Number(form.thdCurrentCritical),
    unbalanceVoltageWarning: Number(form.unbalanceVoltageWarning),
    unbalanceVoltageCritical: Number(form.unbalanceVoltageCritical),
    loadWarning: Number(form.loadWarning) / 100,
    loadCritical: Number(form.loadCritical) / 100,
  };
}

function NumField({
  id,
  label,
  hint,
  value,
  onChange,
  step = "any",
}: {
  id: string;
  label: string;
  hint?: string;
  value: string;
  onChange: (value: string) => void;
  step?: string;
}) {
  return (
    <Field label={label} htmlFor={id} hint={hint}>
      <input
        id={id}
        type="number"
        step={step}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className={inputClass}
      />
    </Field>
  );
}

/** Batas L-N diturunkan dari batas L-L (dibagi sqrt 3), seperti backend. */
function derivedLn(form: ThresholdForm): { warning: string; critical: string } {
  const value = (raw: string) => {
    const number = Number(raw);
    return Number.isFinite(number) ? (number / Math.sqrt(3)).toFixed(1) : "-";
  };
  return {
    warning: `${value(form.voltageLlWarningLow)} – ${value(form.voltageLlWarningHigh)} V`,
    critical: `${value(form.voltageLlCriticalLow)} – ${value(form.voltageLlCriticalHigh)} V`,
  };
}

function ThresholdsEditor() {
  const [form, setForm] = useState<ThresholdForm>(() => toForm(DEFAULT_ALARM_THRESHOLDS));
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      setForm(toForm(await getAlarmThresholds()));
      setError(null);
    } catch (cause) {
      setError(errorMessage(cause, "Gagal memuat ambang alarm."));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const set = <K extends keyof ThresholdForm>(key: K, value: ThresholdForm[K]) =>
    setForm((current) => ({ ...current, [key]: value }));

  function resetDefaults() {
    setForm(toForm(DEFAULT_ALARM_THRESHOLDS));
    setError(null);
    setNotice("Kembali ke nilai bawaan (belum disimpan).");
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (Object.values(form).some((value) => value.trim() === "")) {
      setError("Semua ambang harus diisi dengan angka.");
      return;
    }
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const saved = await updateAlarmThresholds(toPayload(form));
      setForm(toForm(saved));
      setNotice("Ambang disimpan dan langsung dipakai backend.");
    } catch (cause) {
      setError(errorMessage(cause, "Gagal menyimpan ambang alarm."));
    } finally {
      setSaving(false);
    }
  }

  const ln = derivedLn(form);

  return (
    <>
      <PageHeader
        title="Ambang Alarm"
        description="Batas kelistrikan untuk alarm kritis & warning; tersimpan di database dan langsung dipakai backend"
        action={
          <Button variant="secondary" onClick={() => void refresh()} disabled={loading}>
            <RefreshCw className="h-3.5 w-3.5" aria-hidden />
            Muat ulang
          </Button>
        }
      />

      <div className="mb-4 space-y-2">
        {error ? <Alert>{error}</Alert> : null}
        {notice ? <Alert tone="success">{notice}</Alert> : null}
      </div>

      <Card>
        <form onSubmit={handleSubmit} className="space-y-6 p-5">
          <fieldset className="grid gap-3 sm:grid-cols-2">
            <legend className="mb-2 text-xs font-bold uppercase tracking-wider text-brand-700">
              Tegangan antar-fasa (L-L)
            </legend>
            <NumField
              id="volt-warn-low"
              label="Warning bawah (V)"
              value={form.voltageLlWarningLow}
              onChange={(value) => set("voltageLlWarningLow", value)}
            />
            <NumField
              id="volt-warn-high"
              label="Warning atas (V)"
              value={form.voltageLlWarningHigh}
              onChange={(value) => set("voltageLlWarningHigh", value)}
            />
            <NumField
              id="volt-crit-low"
              label="Kritis bawah (V)"
              value={form.voltageLlCriticalLow}
              onChange={(value) => set("voltageLlCriticalLow", value)}
            />
            <NumField
              id="volt-crit-high"
              label="Kritis atas (V)"
              value={form.voltageLlCriticalHigh}
              onChange={(value) => set("voltageLlCriticalHigh", value)}
            />
            <p className="text-xs text-stone-500 sm:col-span-2">
              Batas fasa-netral (L-N) dihitung otomatis: warning {ln.warning}, kritis {ln.critical}.
            </p>
          </fieldset>

          <fieldset className="grid gap-3 sm:grid-cols-2">
            <legend className="mb-2 text-xs font-bold uppercase tracking-wider text-brand-700">
              Power factor
            </legend>
            <NumField
              id="pf-warn"
              label="Warning (<)"
              step="0.01"
              value={form.powerFactorWarning}
              onChange={(value) => set("powerFactorWarning", value)}
            />
            <NumField
              id="pf-crit"
              label="Kritis (<)"
              step="0.01"
              value={form.powerFactorCritical}
              onChange={(value) => set("powerFactorCritical", value)}
            />
          </fieldset>

          <fieldset className="grid gap-3 sm:grid-cols-2">
            <legend className="mb-2 text-xs font-bold uppercase tracking-wider text-brand-700">
              Frekuensi (deviasi dari 50 Hz)
            </legend>
            <NumField
              id="freq-warn"
              label="Warning (Hz)"
              step="0.05"
              value={form.frequencyWarning}
              onChange={(value) => set("frequencyWarning", value)}
            />
            <NumField
              id="freq-crit"
              label="Kritis (Hz)"
              step="0.05"
              value={form.frequencyCritical}
              onChange={(value) => set("frequencyCritical", value)}
            />
          </fieldset>

          <fieldset className="grid gap-3 sm:grid-cols-2">
            <legend className="mb-2 text-xs font-bold uppercase tracking-wider text-brand-700">
              THD arus
            </legend>
            <NumField
              id="thd-warn"
              label="Warning (%)"
              step="0.1"
              value={form.thdCurrentWarning}
              onChange={(value) => set("thdCurrentWarning", value)}
            />
            <NumField
              id="thd-crit"
              label="Kritis (%)"
              step="0.1"
              value={form.thdCurrentCritical}
              onChange={(value) => set("thdCurrentCritical", value)}
            />
          </fieldset>

          <fieldset className="grid gap-3 sm:grid-cols-2">
            <legend className="mb-2 text-xs font-bold uppercase tracking-wider text-brand-700">
              Unbalance tegangan
            </legend>
            <NumField
              id="unbalance-warn"
              label="Warning (%)"
              step="0.1"
              value={form.unbalanceVoltageWarning}
              onChange={(value) => set("unbalanceVoltageWarning", value)}
            />
            <NumField
              id="unbalance-crit"
              label="Kritis (%)"
              step="0.1"
              value={form.unbalanceVoltageCritical}
              onChange={(value) => set("unbalanceVoltageCritical", value)}
            />
          </fieldset>

          <fieldset className="grid gap-3 sm:grid-cols-2">
            <legend className="mb-2 text-xs font-bold uppercase tracking-wider text-brand-700">
              Beban (% daya rating meter)
            </legend>
            <NumField
              id="load-warn"
              label="Warning (%)"
              step="1"
              value={form.loadWarning}
              onChange={(value) => set("loadWarning", value)}
            />
            <NumField
              id="load-crit"
              label="Kritis (%)"
              step="1"
              value={form.loadCritical}
              onChange={(value) => set("loadCritical", value)}
            />
          </fieldset>

          <p className="rounded-lg bg-stone-50 px-3 py-2 text-xs text-stone-600">
            Perubahan ambang langsung dipakai pada siklus evaluasi alarm berikutnya dan dicatat di audit log.
          </p>

          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={resetDefaults}>
              Reset bawaan
            </Button>
            <Button type="submit" disabled={saving || loading}>
              <Save className="h-3.5 w-3.5" aria-hidden />
              {saving ? "Menyimpan..." : "Simpan ambang"}
            </Button>
          </div>
        </form>
      </Card>
    </>
  );
}

export default function AdminThresholdsPage() {
  return (
    <AdminOnly>
      <ThresholdsEditor />
    </AdminOnly>
  );
}
