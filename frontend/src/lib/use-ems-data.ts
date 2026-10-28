"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getDevices, getRealtimeUrl, getSummary, type Summary } from "@/lib/api";
import type { Device } from "@/lib/types";

export function useEMSData() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [realtime, setRealtime] = useState(false);
  const lastRealtimeRefresh = useRef(0);

  const refresh = useCallback(async () => {
    try {
      const [nextDevices, nextSummary] = await Promise.all([
        getDevices(),
        getSummary(),
      ]);
      setDevices(nextDevices);
      setSummary(nextSummary);
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Gagal memuat data EMS.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const poll = window.setInterval(() => void refresh(), 15_000);
    let active = true;
    let retry: number | undefined;
    let socket: WebSocket;

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
          const message: { type?: string } = JSON.parse(event.data);
          if (message.type !== "telemetry" && message.type !== "snapshot") return;
          const now = Date.now();
          if (now - lastRealtimeRefresh.current < 1_000) return;
          lastRealtimeRefresh.current = now;
          void refresh();
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
      socket.close();
    };
  }, [refresh]);

  return { devices, summary, loading, error, realtime, refresh };
}
