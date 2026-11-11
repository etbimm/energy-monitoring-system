"""Buat User Role Diagram (UML use case) EMS: SVG, draw.io, dan PNG.

Sumber hak akses (cek ulang bila role berubah):
- backend/app/api/__init__.py   : router yang wajib login (LOGIN_REQUIRED)
- backend/app/api/deps.py       : get_current_user, require_admin
- backend/app/api/admin.py      : seluruh /api/admin/* khusus admin
- backend/app/api/alarms.py     : acknowledge alarm khusus admin
- backend/app/api/auth.py       : login, logout, me, change-password

Jalankan:  py scripts/generate_user_role_diagram.py
Hasil   :  docs/user-role/user-role-diagram.{svg,drawio,png}
"""
from __future__ import annotations

import math
import shutil
import subprocess
from dataclasses import dataclass
from html import escape
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "docs" / "user-role"
NAME = "user-role-diagram"
W, H = 1500, 1215
FONT = "Arial, Helvetica, sans-serif"

# Palet sama dengan flowchart (scripts/generate_flowcharts.py).
NAVY = "#0B3D6E"
INK = "#33475B"
MUTED = "#5A6B7D"
VIEW_FILL, VIEW_STROKE = "#E4EDF8", "#1F4E79"
ADMIN_FILL, ADMIN_STROKE = "#E6F5F2", "#22A699"
PKG_FILL = "#F8FAFC"


@dataclass
class UseCase:
    id: str
    text: str
    x: float
    y: float
    w: float
    h: float
    admin: bool = False

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2

    @property
    def left(self) -> tuple[float, float]:
        return self.x, self.cy

    @property
    def right(self) -> tuple[float, float]:
        return self.x + self.w, self.cy

    def edge_point(self, tx: float, ty: float) -> tuple[float, float]:
        """Titik pada tepi elips searah ke (tx, ty)."""
        dx, dy = tx - self.cx, ty - self.cy
        a, b = self.w / 2, self.h / 2
        if dx == 0 and dy == 0:
            return self.cx, self.cy
        t = 1 / math.sqrt((dx / a) ** 2 + (dy / b) ** 2)
        return self.cx + dx * t, self.cy + dy * t


@dataclass
class Actor:
    id: str
    label: str
    note: str
    x: float  # pusat
    y: float  # puncak kepala

    @property
    def hand(self) -> tuple[float, float]:
        return self.x, self.y + 38


@dataclass
class Box:
    id: str
    title: str
    x: float
    y: float
    w: float
    h: float
    kind: str  # system | package-view | package-admin


# ---------------------------------------------------------------------------
# Isi diagram (diturunkan dari kode, lihat docstring)
# ---------------------------------------------------------------------------

SYSTEM = Box("system", "Energy Monitoring System — Web Dashboard Java Wood Pellet", 200, 40, 1060, 960, "system")
PKG_VIEW = Box("pkg_view", "Monitoring (Viewer & Admin)", 235, 95, 400, 880, "package-view")
PKG_ADMIN = Box("pkg_admin", "Administrasi (khusus Admin)", 665, 95, 560, 880, "package-admin")

VIEW_X, VIEW_W, VIEW_H, VIEW_STEP = 275, 320, 58, 86
_view = [
    ("uc_login", "Login"),
    ("uc_logout", "Logout"),
    ("uc_password", "Ganti password sendiri\n(Akun Saya)"),
    ("uc_overview", "Lihat Overview\n(ringkasan daya & energi)"),
    ("uc_realtime", "Pantau data Real-time"),
    ("uc_history", "Lihat History\n(grafik & total energi)"),
    ("uc_pq", "Lihat Power Quality\n(THD, unbalance, per fasa)"),
    ("uc_devices", "Lihat daftar Device\n& status meter"),
    ("uc_alarms", "Lihat Alarm"),
]
VIEW_CASES = [
    UseCase(cid, text, VIEW_X, 145 + i * VIEW_STEP, VIEW_W, VIEW_H) for i, (cid, text) in enumerate(_view)
]

MAIN_X, MAIN_W, MAIN_H = 1030, 180, 64
SUB_X, SUB_W, SUB_H = 690, 245, 46
ADMIN_MAIN = [
    UseCase("uc_users", "Kelola Akun", MAIN_X, 300, MAIN_W, MAIN_H, True),
    UseCase("uc_devmgmt", "Kelola Device", MAIN_X, 600, MAIN_W, MAIN_H, True),
    UseCase("uc_audit", "Lihat Audit Log", MAIN_X, 760, MAIN_W, MAIN_H, True),
    UseCase("uc_ack", "Acknowledge Alarm", MAIN_X, 870, MAIN_W, MAIN_H, True),
]
_user_subs = [
    ("uc_u_search", "Cari & filter akun"),
    ("uc_u_create", "Tambah akun"),
    ("uc_u_edit", "Ubah nama & role akun"),
    ("uc_u_reset", "Reset password akun"),
    ("uc_u_toggle", "Nonaktifkan / aktifkan akun"),
    ("uc_u_delete", "Hapus akun permanen"),
]
_dev_subs = [
    ("uc_d_create", "Tambah device\n(model/peran/jalur \"Lainnya\")"),
    ("uc_d_edit", "Edit konfigurasi device"),
    ("uc_d_toggle", "Nonaktifkan / aktifkan device"),
]
USER_SUBS = [UseCase(cid, t, SUB_X, 140 + i * 62, SUB_W, SUB_H, True) for i, (cid, t) in enumerate(_user_subs)]
DEV_SUBS = [UseCase(cid, t, SUB_X, 545 + i * 62, SUB_W, SUB_H if "\n" not in t else 56, True)
            for i, (cid, t) in enumerate(_dev_subs)]

VIEWER = Actor("actor_viewer", "Viewer", "melihat data", 105, 470)
ADMIN = Actor("actor_admin", "Admin", "mengelola sistem", 1400, 540)

ALL_CASES = VIEW_CASES + ADMIN_MAIN + USER_SUBS + DEV_SUBS
BY_ID = {c.id: c for c in ALL_CASES}

# (sumber, tujuan, jenis)
ASSOC = [(VIEWER, c) for c in VIEW_CASES] + [(ADMIN, c) for c in ADMIN_MAIN]
INCLUDES = [("uc_users", s.id) for s in USER_SUBS] + [("uc_devmgmt", s.id) for s in DEV_SUBS]
EXTENDS = [("uc_ack", "uc_alarms")]  # acknowledge memperluas "Lihat Alarm"

NOTES = [
    "Catatan:",
    "1. Semua use case selain Login mensyaratkan sesi login (JWT di cookie httpOnly). Tanpa login, halaman dialihkan ke /login.",
    "2. Admin mewarisi seluruh use case Viewer (generalisasi). Batasan diterapkan di backend (401/403), menu admin hanya disembunyikan di frontend.",
    "3. Admin tidak dapat menurunkan role, menonaktifkan, atau menghapus akunnya sendiri; minimal satu admin aktif harus tetap ada.",
    "4. Admin pertama dibuat lewat CLI server: python -m app.cli create-admin (tidak ada registrasi publik).",
]


# ---------------------------------------------------------------------------
# SVG
# ---------------------------------------------------------------------------

def _text(x: float, y: float, text: str, size: float = 13, weight: str = "normal", fill: str = NAVY,
          anchor: str = "middle", line: float = 16) -> str:
    lines = text.split("\n")
    top = y - (len(lines) - 1) * line / 2
    return "".join(
        f'<text x="{x:.1f}" y="{top + i * line:.1f}" text-anchor="{anchor}" dominant-baseline="central" '
        f'font-family="{FONT}" font-size="{size}" font-weight="{weight}" fill="{fill}">{escape(t)}</text>'
        for i, t in enumerate(lines)
    )


def _box_svg(b: Box) -> str:
    if b.kind == "system":
        return (
            f'<rect x="{b.x}" y="{b.y}" width="{b.w}" height="{b.h}" fill="#FFFFFF" stroke="{NAVY}" stroke-width="2"/>'
            f'<rect x="{b.x}" y="{b.y}" width="{b.w}" height="40" fill="{NAVY}"/>'
            + _text(b.x + b.w / 2, b.y + 20, b.title, 16, "bold", "#FFFFFF")
        )
    stroke = VIEW_STROKE if b.kind == "package-view" else ADMIN_STROKE
    return (
        f'<rect x="{b.x}" y="{b.y}" width="{b.w}" height="{b.h}" rx="8" fill="{PKG_FILL}" stroke="{stroke}" '
        f'stroke-width="1.4" stroke-dasharray="6 4"/>'
        + _text(b.x + 14, b.y + 20, b.title, 14, "bold", stroke, "start")
    )


def _case_svg(c: UseCase) -> str:
    fill, stroke = (ADMIN_FILL, ADMIN_STROKE) if c.admin else (VIEW_FILL, VIEW_STROKE)
    return (
        f'<ellipse cx="{c.cx:.1f}" cy="{c.cy:.1f}" rx="{c.w / 2:.1f}" ry="{c.h / 2:.1f}" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="1.5"/>' + _text(c.cx, c.cy, c.text, 13)
    )


def _actor_svg(a: Actor) -> str:
    x, y = a.x, a.y
    s = f'stroke="{NAVY}" stroke-width="2.2" fill="none" stroke-linecap="round"'
    return (
        f'<circle cx="{x}" cy="{y + 14}" r="14" fill="#FFFFFF" stroke="{NAVY}" stroke-width="2.2"/>'
        f'<line x1="{x}" y1="{y + 28}" x2="{x}" y2="{y + 66}" {s}/>'
        f'<line x1="{x - 24}" y1="{y + 40}" x2="{x + 24}" y2="{y + 40}" {s}/>'
        f'<line x1="{x}" y1="{y + 66}" x2="{x - 20}" y2="{y + 96}" {s}/>'
        f'<line x1="{x}" y1="{y + 66}" x2="{x + 20}" y2="{y + 96}" {s}/>'
        + _text(x, y + 114, a.label, 15, "bold", NAVY)
        + _text(x, y + 132, f"({a.note})", 12, "normal", MUTED)
    )


def _dashed_arrow(src: UseCase, dst: UseCase, label: str, sides: bool = False) -> str:
    if sides:
        # «include»: dari sisi kiri use case utama ke sisi kanan sub use case.
        (x1, y1), (x2, y2) = src.left, dst.right
    else:
        x1, y1 = src.edge_point(dst.cx, dst.cy)
        x2, y2 = dst.edge_point(src.cx, src.cy)
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    return (
        f'<path d="M{x1:.1f},{y1:.1f} L{x2:.1f},{y2:.1f}" fill="none" stroke="{INK}" stroke-width="1.2" '
        f'stroke-dasharray="6 4" marker-end="url(#open)"/>'
        f'<rect x="{mx - 32:.1f}" y="{my - 9:.1f}" width="64" height="18" fill="#FFFFFF" opacity="0.9"/>'
        + _text(mx, my, label, 11, "normal", INK)
    )


def to_svg() -> str:
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">',
        "<defs>"
        f'<marker id="open" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="9" markerHeight="9" orient="auto-start-reverse">'
        f'<path d="M0,0 L10,5 L0,10" fill="none" stroke="{INK}" stroke-width="1.4"/></marker>'
        f'<marker id="triangle" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="14" markerHeight="14" orient="auto-start-reverse">'
        f'<path d="M0,0 L12,6 L0,12 z" fill="#FFFFFF" stroke="{INK}" stroke-width="1.4"/></marker>'
        "</defs>",
        f'<rect width="{W}" height="{H}" fill="#FFFFFF"/>',
        _text(W / 2, 18, "User Role Diagram (Use Case) — Energy Monitoring System", 17, "bold", NAVY),
        _box_svg(SYSTEM), _box_svg(PKG_VIEW), _box_svg(PKG_ADMIN),
    ]
    # Asosiasi aktor - use case
    for actor, case in ASSOC:
        ax, ay = actor.hand
        # Mulai dari tangan yang menghadap use case, agar garis tidak memotong label aktor.
        ax += 24 if actor is VIEWER else -24
        # Ujung garis di sisi elips yang menghadap aktor: tidak memotong elips lain.
        ex, ey = case.left if actor is VIEWER else case.right
        parts.append(f'<line x1="{ax}" y1="{ay}" x2="{ex:.1f}" y2="{ey:.1f}" stroke="{INK}" stroke-width="1.3"/>')
    for src, dst in INCLUDES:
        parts.append(_dashed_arrow(BY_ID[src], BY_ID[dst], "«include»", sides=True))
    for src, dst in EXTENDS:
        parts.append(_dashed_arrow(BY_ID[src], BY_ID[dst], "«extend»"))
    # Generalisasi Admin -> Viewer, lewat bawah kotak sistem
    gy = SYSTEM.y + SYSTEM.h + 25
    parts.append(
        f'<path d="M{ADMIN.x},{ADMIN.y + 140} L{ADMIN.x},{gy} L{VIEWER.x},{gy} L{VIEWER.x},{VIEWER.y + 140}" '
        f'fill="none" stroke="{INK}" stroke-width="1.4" marker-end="url(#triangle)"/>'
    )
    parts.append(f'<rect x="{W / 2 - 230}" y="{gy - 11}" width="460" height="22" fill="#FFFFFF"/>')
    parts.append(_text(W / 2, gy, "generalisasi: Admin mewarisi semua hak akses Viewer", 12.5, "bold", INK))
    for case in ALL_CASES:
        parts.append(_case_svg(case))
    parts.append(_actor_svg(VIEWER))
    parts.append(_actor_svg(ADMIN))
    # Catatan
    ny = gy + 34
    parts.append(f'<rect x="40" y="{ny}" width="{W - 80}" height="{22 * len(NOTES) + 16}" rx="6" '
                 f'fill="#FFFBEA" stroke="#D3A52C" stroke-width="1"/>')
    for i, note in enumerate(NOTES):
        parts.append(_text(56, ny + 19 + i * 22, note, 12.5, "bold" if i == 0 else "normal", INK, "start"))
    parts.append("</svg>")
    return "".join(parts)


# ---------------------------------------------------------------------------
# draw.io (bisa diedit di app.diagrams.net / draw.io desktop)
# ---------------------------------------------------------------------------

def _attr(text: str) -> str:
    return escape(text.replace("\n", "<br>"), quote=True)


def to_drawio() -> str:
    cells: list[str] = ['<mxCell id="0"/>', '<mxCell id="1" parent="0"/>']

    def vertex(cid: str, value: str, style: str, x: float, y: float, w: float, h: float) -> None:
        cells.append(
            f'<mxCell id="{cid}" value="{_attr(value)}" style="{style}" vertex="1" parent="1">'
            f'<mxGeometry x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{h:.0f}" as="geometry"/></mxCell>'
        )

    def edge(cid: str, src: str, dst: str, style: str, value: str = "", points: list[tuple[float, float]] | None = None) -> None:
        pts = ""
        if points:
            pts = '<Array as="points">' + "".join(f'<mxPoint x="{x:.0f}" y="{y:.0f}"/>' for x, y in points) + "</Array>"
        cells.append(
            f'<mxCell id="{cid}" value="{_attr(value)}" style="{style}" edge="1" parent="1" source="{src}" target="{dst}">'
            f'<mxGeometry relative="1" as="geometry">{pts}</mxGeometry></mxCell>'
        )

    font = f"fontFamily=Arial;fontColor={NAVY};"
    vertex("title", "User Role Diagram (Use Case) — Energy Monitoring System",
           f"text;html=1;align=center;verticalAlign=middle;fontStyle=1;fontSize=17;{font}", 0, 4, W, 28)
    vertex(SYSTEM.id, SYSTEM.title,
           f"swimlane;html=1;startSize=40;fillColor={NAVY};swimlaneFillColor=#FFFFFF;strokeColor={NAVY};"
           f"fontColor=#FFFFFF;fontStyle=1;fontSize=16;fontFamily=Arial;container=0;",
           SYSTEM.x, SYSTEM.y, SYSTEM.w, SYSTEM.h)
    for b, color in ((PKG_VIEW, VIEW_STROKE), (PKG_ADMIN, ADMIN_STROKE)):
        vertex(b.id, b.title,
               f"rounded=1;arcSize=2;html=1;dashed=1;fillColor={PKG_FILL};strokeColor={color};fontColor={color};"
               f"fontStyle=1;fontSize=14;fontFamily=Arial;align=left;verticalAlign=top;spacingLeft=12;spacingTop=6;",
               b.x, b.y, b.w, b.h)
    for c in ALL_CASES:
        fill, stroke = (ADMIN_FILL, ADMIN_STROKE) if c.admin else (VIEW_FILL, VIEW_STROKE)
        vertex(c.id, c.text, f"ellipse;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};fontSize=13;{font}",
               c.x, c.y, c.w, c.h)
    for a in (VIEWER, ADMIN):
        vertex(a.id, f"{a.label}\n({a.note})",
               f"shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;html=1;outlineConnect=0;"
               f"strokeColor={NAVY};strokeWidth=2;fillColor=#FFFFFF;fontStyle=1;fontSize=15;{font}",
               a.x - 24, a.y, 48, 96)
    assoc = f"endArrow=none;html=1;strokeColor={INK};entryY=0.5;"
    for i, (actor, case) in enumerate(ASSOC):
        side = "entryX=0;" if actor is VIEWER else "entryX=1;"
        edge(f"as{i}", actor.id, case.id, assoc + side)
    dashed = f"endArrow=open;endSize=10;dashed=1;html=1;strokeColor={INK};fontSize=11;fontColor={INK};labelBackgroundColor=#FFFFFF;"
    for i, (src, dst) in enumerate(INCLUDES):
        edge(f"inc{i}", src, dst, dashed + "exitX=0;exitY=0.5;entryX=1;entryY=0.5;", "«include»")
    for i, (src, dst) in enumerate(EXTENDS):
        edge(f"ext{i}", src, dst, dashed, "«extend»")
    gy = SYSTEM.y + SYSTEM.h + 25
    edge("gen", ADMIN.id, VIEWER.id,
         f"endArrow=block;endFill=0;endSize=14;html=1;rounded=0;edgeStyle=orthogonalEdgeStyle;strokeColor={INK};"
         f"exitX=0.5;exitY=1;entryX=0.5;entryY=1;fontStyle=1;fontSize=12;fontColor={INK};labelBackgroundColor=#FFFFFF;",
         "generalisasi: Admin mewarisi semua hak akses Viewer", [(ADMIN.x, gy), (VIEWER.x, gy)])
    ny = gy + 34
    vertex("notes", "\n".join(NOTES),
           f"text;html=1;align=left;verticalAlign=top;whiteSpace=wrap;rounded=1;fillColor=#FFFBEA;strokeColor=#D3A52C;"
           f"spacing=10;fontSize=12;fontFamily=Arial;fontColor={INK};",
           40, ny, W - 80, 22 * len(NOTES) + 16)

    return (
        '<mxfile host="app.diagrams.net" type="device">'
        '<diagram id="user-role" name="User Role Diagram">'
        f'<mxGraphModel dx="{W}" dy="{H}" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" '
        f'fold="1" page="1" pageScale="1" pageWidth="{W}" pageHeight="{H}" math="0" shadow="0"><root>'
        + "".join(cells)
        + "</root></mxGraphModel></diagram></mxfile>\n"
    )


# ---------------------------------------------------------------------------
# PNG (opsional): render SVG dengan Edge/Chrome headless bila tersedia
# ---------------------------------------------------------------------------

def _browser() -> str | None:
    candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    ]
    for path in candidates:
        if Path(path).exists():
            return path
    return shutil.which("chromium") or shutil.which("google-chrome") or shutil.which("msedge")


def to_png(svg_path: Path, png_path: Path) -> bool:
    browser = _browser()
    if browser is None:
        return False
    subprocess.run(
        [browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=2",
         f"--window-size={W},{H}", f"--screenshot={png_path}", svg_path.as_uri()],
        check=False, capture_output=True, timeout=120,
    )
    return png_path.exists()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    svg_path = OUT / f"{NAME}.svg"
    svg_path.write_text(to_svg(), encoding="utf-8")
    (OUT / f"{NAME}.drawio").write_text(to_drawio(), encoding="utf-8")
    png = to_png(svg_path, OUT / f"{NAME}.png")
    print(f"User role diagram ditulis ke {OUT}" + ("" if png else " (PNG dilewati: Edge/Chrome tidak ditemukan)"))


if __name__ == "__main__":
    main()
