import {
  Activity,
  BarChart3,
  Cpu,
  History,
  LayoutDashboard,
  Server,
  Siren,
  Users,
  Waves,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

export const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/realtime", label: "Real-time", icon: Activity },
  { href: "/history", label: "History", icon: BarChart3 },
  { href: "/power-quality", label: "Power Quality", icon: Waves },
  { href: "/devices", label: "Devices", icon: Cpu },
  { href: "/alarms", label: "Alarms", icon: Siren },
];

/** Menu khusus admin (backend tetap menolak akses non-admin). */
export const ADMIN_NAV_ITEMS: NavItem[] = [
  { href: "/admin/users", label: "Kelola Akun", icon: Users },
  { href: "/admin/devices", label: "Kelola Device", icon: Server },
  { href: "/admin/audit", label: "Audit Log", icon: History },
];
