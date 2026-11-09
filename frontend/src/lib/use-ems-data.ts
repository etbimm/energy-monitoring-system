"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { getDevices, getRealtimeUrl, getSummary, type Summary } from "@/lib/api";
import { DEMO_MODE } from "@/lib/demo-mode";
import { DEVICES, getTotals } from "@/lib/mock-data";
import { applyTelemetry, withLiveTotals, type TelemetryMessage } from "@/lib/realtime";
import type { Device } from "@/lib/types";

const EMPTY_SUMMARY: Summary = {
  totalPower: 0,
  totalApparentPower: 0,
  totalReactivePower: 0,
  energyToday: 0,
  online: 0,
  warning: 0,
  offline: 0,
  total: 0,
};

/** Sinkronisasi penuh lewat REST (status alarm, energi hari ini, jumlah status). */
const REST_SYNC_MS = 60_000;
/** Pesan WebSocket dikumpulkan lalu diterapkan sekali per interval ini. */
const REALTIME_FLUSH_MS = 1_000;
/** Jarak minimum sinkronisasi REST yang dipicu meter baru (belum ada di daftar). */
const UNKNOWN_DEVICE_SYNC_MS = 10_000;

export function useEMSData() {
  const [devices, setDevices] = useState<Device[]>(DEMO_MODE ? DEVICES : []);
  const [summary, setSummary] = useState<Summary>(DEMO_MODE ? getTotals() : EMPTY_SUMMARY);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isDemo, setIsDemo] = useState(DEMO_MODE);
  const [realtime, setRealtime] = useState(false);
  const pending = useRef(new Map<string, TelemetryMessage>());
  const isDemoRef = useRef(DEMO_MODE);
  // Kode meter yang sudah ada di daftar; dipakai untuk mengenali meter baru.
  const knownIds = useRef(new Set<string>());
  const lastUnknownSync = useRef(0);

  useEffect(() => {
    knownIds.current = new Set(devices.map((device) => device.id));
  }, [devices]);

  const refresh = useCallback(async () => {
    try {
      const [nextDevices, nextSummary] = await Promise.all([
        getDevices(),
        getSummary(),
      ]);
      if (
        nextDevices.length === 0 ||
        nextSummary.total === 0 ||
        nextDevices.every((device) => !device.lastSeen)
      ) {
        if (DEMO_MODE) {
          setDevices(DEVICES);
          setSummary(getTotals());
          setIsDemo(true);
          isDemoRef.current = true;
          setError("Backend belum memiliki data meter. Menampilkan data simulasi.");
          return;
        }
        setDevices(nextDevices);
        setSummary(nextSummary);
        setIsDemo(false);
        isDemoRef.current = false;
        setError("Backend belum memiliki data meter.");
        return;
      }
      setDevices(nextDevices);
      setSummary(nextSummary);
      setIsDemo(false);
      isDemoRef.current = false;
      setError(null);
    } catch (cause) {
      if (DEMO_MODE) {
        setDevices(DEVICES);
        setSummary(getTotals());
        setIsDemo(true);
        isDemoRef.current = true;
      } else {
        setDevices([]);
        setSummary(EMPTY_SUMMARY);
        setIsDemo(false);
        isDemoRef.current = false;
      }
      setError(cause instanceof Error ? cause.message : "Gagal memuat data EMS.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const poll = window.setInterval(() => void refresh(), REST_SYNC_MS);
    let active = true;
    let retry: number | undefined;
    let socket: WebSocket;

    // Terapkan pesan yang terkumpul ke state sekali per detik (bukan per pesan),
    // tanpa memanggil REST: data sudah ada di payload WebSocket.
    const flush = window.setInterval(() => {
      if (pending.current.size === 0 || isDemoRef.current) {
        pending.current.clear();
        return;
      }
      const updates = new Map(pending.current);
      pending.current.clear();

      // Meter yang belum ada di daftar (mis. baru ditambahkan di database):
      // minta daftar lengkap lewat REST sekarang, tidak menunggu sinkron 60 detik.
      const hasUnknown = [...updates.keys()].some((code) => !knownIds.current.has(code));
      const now = Date.now();
      if (hasUnknown && now - lastUnknownSync.current >= UNKNOWN_DEVICE_SYNC_MS) {
        lastUnknownSync.current = now;
        void refresh();
      }

      setDevices((current) =>
        current.map((device) => {
          const message = updates.get(device.id);
          return message ? applyTelemetry(device, message) : device;
        }),
      );
    }, REALTIME_FLUSH_MS);

    const queue = (message: TelemetryMessage) => {
      if (message && typeof message.device_code === "string") {
        pending.current.set(message.device_code, message);
      }
    };

    const connect = () => {
      if (!active) return;
      socket = new WebSocket(getRealtimeUrl());
      socket.onopen = () => setRealtime(true);
      socket.onclose = () => {
        setRealtime(false);
        if (active) retry = window.setTimeout(connect, 3_000);
      };
      socket.onerror = () => socket.close();
      socket.onmessage = (event) => {
        try {
          const message: { type?: string; payload?: unknown } = JSON.parse(event.data);
          if (message.type === "telemetry") {
            queue(message.payload as TelemetryMessage);
          } else if (message.type === "snapshot" && Array.isArray(message.payload)) {
            message.payload.forEach((item) => queue(item as TelemetryMessage));
          } else if (message.type === "alarm") {
            // Alarm baru mengubah status warning/critical: sinkronkan lewat REST.
            void refresh();
          }
        } catch {
          setError("Backend mengirim pesan realtime yang tidak valid.");
        }
      };
    };
    connect();

    return () => {
      active = false;
      if (retry !== undefined) window.clearTimeout(retry);
      window.clearInterval(poll);
      window.clearInterval(flush);
      socket.close();
    };
  }, [refresh]);

  // Total daya mengikuti data realtime; energi hari ini & jumlah status dari REST.
  const liveSummary = useMemo(
    () => (isDemo ? summary : withLiveTotals(summary, devices)),
    [isDemo, summary, devices],
  );

  return { devices, summary: liveSummary, loading, error, isDemo, realtime, refresh };
}
