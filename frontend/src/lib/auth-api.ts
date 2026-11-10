import { request } from "@/lib/api";
import type { MeterCapabilities, MeterRole } from "@/lib/types";

export type UserRole = "admin" | "viewer";

export interface User {
  id: number;
  username: string;
  fullName: string;
  role: UserRole;
  isActive: boolean;
  lastLoginAt: string | null;
  createdAt: string | null;
}

export const ROLE_LABEL: Record<UserRole, string> = {
  admin: "Admin",
  viewer: "Viewer",
};

/* ------------------------------------------------------------------ */
/* Sesi login                                                          */
/* ------------------------------------------------------------------ */

export function login(username: string, password: string): Promise<User> {
  return request("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export function logout(): Promise<{ ok: boolean }> {
  return request("/api/auth/logout", { method: "POST" });
}

export function getMe(): Promise<User> {
  return request("/api/auth/me");
}

export function changePassword(currentPassword: string, newPassword: string) {
  return request<{ ok: boolean }>("/api/auth/change-password", {
    method: "POST",
    body: JSON.stringify({ currentPassword, newPassword }),
  });
}

/* ------------------------------------------------------------------ */
/* Admin: akun pengguna                                                */
/* ------------------------------------------------------------------ */

export function listUsers(): Promise<User[]> {
  return request("/api/admin/users");
}

export function createUser(input: {
  username: string;
  fullName: string;
  role: UserRole;
  password: string;
}): Promise<User> {
  return request("/api/admin/users", { method: "POST", body: JSON.stringify(input) });
}

export function updateUser(
  id: number,
  input: Partial<Pick<User, "fullName" | "role" | "isActive">>,
): Promise<User> {
  return request(`/api/admin/users/${id}`, { method: "PATCH", body: JSON.stringify(input) });
}

export function resetUserPassword(id: number, password: string) {
  return request<{ ok: boolean }>(`/api/admin/users/${id}/reset-password`, {
    method: "POST",
    body: JSON.stringify({ password }),
  });
}

/* ------------------------------------------------------------------ */
/* Admin: device                                                       */
/* ------------------------------------------------------------------ */

export type Transport = "rs485" | "ethernet";

export interface DeviceModelOption {
  model: string;
  brand: string;
  label: string;
  capabilities: MeterCapabilities;
  /** false = model "Lainnya": belum ada profil register, belum dibaca akuisisi. */
  supported: boolean;
}

export interface DeviceConfig {
  id: string;
  name: string;
  location: string | null;
  brand: string | null;
  model: string;
  role: MeterRole;
  transport: Transport | null;
  modbusHost: string | null;
  modbusPort: number;
  modbusAddress: number | null;
  ratedPowerKw: number | null;
  isActive: boolean;
  /** false = model belum punya profil register (tidak bisa dibaca mode modbus). */
  profileSupported: boolean;
  lastSeen: string | null;
  createdAt: string | null;
  updatedAt: string | null;
}

export interface DeviceInput {
  name: string;
  location: string | null;
  model: string;
  /** Wajib untuk model "Lainnya"; diabaikan backend untuk model yang dikenal. */
  brand?: string;
  role: MeterRole;
  transport: Transport;
  modbusHost: string;
  modbusPort: number;
  modbusAddress: number;
  ratedPowerKw: number | null;
}

export function listDeviceModels(): Promise<DeviceModelOption[]> {
  return request("/api/admin/device-models");
}

export function listDeviceConfigs(): Promise<DeviceConfig[]> {
  return request("/api/admin/devices");
}

export function createDevice(input: DeviceInput & { deviceCode: string }): Promise<DeviceConfig> {
  return request("/api/admin/devices", { method: "POST", body: JSON.stringify(input) });
}

export function updateDevice(
  code: string,
  input: Partial<DeviceInput> & { isActive?: boolean },
): Promise<DeviceConfig> {
  return request(`/api/admin/devices/${encodeURIComponent(code)}`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

/* ------------------------------------------------------------------ */
/* Admin: audit log                                                    */
/* ------------------------------------------------------------------ */

export interface AuditEntry {
  id: number;
  username: string | null;
  action: string;
  target: string | null;
  detail: Record<string, unknown>;
  createdAt: string;
}

export function listAuditLog(limit = 200): Promise<AuditEntry[]> {
  return request(`/api/admin/audit-log?limit=${limit}`);
}
