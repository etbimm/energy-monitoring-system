"""Generator flowchart program EMS (SVG + draw.io + halaman pratinjau).

Simbol mengikuti template laporan:
  Terminator, Proses, Keputusan, Input/Output, Subrutin, Penyimpanan data, Konektor.

Jalankan dari root repo:  py scripts/generate_flowcharts.py
Hasil ditulis ke docs/flowchart/.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from html import escape
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "docs" / "flowchart"

# ---------------------------------------------------------------- gaya
NAVY = "#0B3D6E"
BLUE_FILL = "#E4EDF8"
BLUE_LINE = "#1F4E79"
TEAL_FILL = "#E6F5F2"
TEAL_LINE = "#22A699"
LINE = "#33475B"
FONT = "Arial, Helvetica, sans-serif"
FONT_SIZE = 12.5

CW = 270  # jarak antarkolom
RH = 112  # jarak antarbaris
SKEW = 18  # kemiringan jajaran genjang

SIZES = {
    "T": (180, 48),
    "P": (230, 58),
    "D": (196, 86),
    "IO": (240, 58),
    "S": (230, 58),
    "DB": (230, 66),
    "C": (38, 38),
}


@dataclass
class Node:
    id: str
    kind: str
    col: float
    row: float
    text: str

    @property
    def x(self) -> float:
        return self.col * CW

    @property
    def y(self) -> float:
        return self.row * RH

    @property
    def w(self) -> float:
        return SIZES[self.kind][0]

    @property
    def h(self) -> float:
        return SIZES[self.kind][1]

    def port(self, side: str) -> tuple[float, float]:
        half_w = self.w / 2
        if self.kind == "IO" and side in "lr":
            half_w -= SKEW / 2
        return {
            "t": (self.x, self.y - self.h / 2),
            "b": (self.x, self.y + self.h / 2),
            "l": (self.x - half_w, self.y),
            "r": (self.x + half_w, self.y),
        }[side]


@dataclass
class Edge:
    a: str
    b: str
    label: str | None = None
    fp: str = "b"
    tp: str = "t"
    lane: float | None = None  # kolom jalur balik (untuk loop)
    via: list[tuple[float, float]] | None = None  # titik belok manual (kolom, baris)


@dataclass
class Chart:
    slug: str
    title: str
    desc: str
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)

    def n(self, id: str, kind: str, col: float, row: float, text: str) -> None:
        self.nodes.append(Node(id, kind, col, row, text))

    def e(self, a: str, b: str, label: str | None = None, fp: str = "b", tp: str = "t",
          lane: float | None = None, via: list[tuple[float, float]] | None = None) -> None:
        self.edges.append(Edge(a, b, label, fp, tp, lane, via))

    def node(self, id: str) -> Node:
        return next(n for n in self.nodes if n.id == id)


# ---------------------------------------------------------------- routing
def route(chart: Chart, edge: Edge) -> list[tuple[float, float]]:
    a, b = chart.node(edge.a), chart.node(edge.b)
    p1, p2 = a.port(edge.fp), b.port(edge.tp)
    fp, tp = edge.fp, edge.tp
    pts = [p1]
    lane_x = edge.lane * CW if edge.lane is not None else None
    if edge.via:
        return pts + [(cx * CW, cy * RH) for cx, cy in edge.via] + [p2]
    if fp in "tb" and tp in "tb":
        if abs(p1[0] - p2[0]) > 0.5:
            mid = (p1[1] + p2[1]) / 2
            pts += [(p1[0], mid), (p2[0], mid)]
    elif fp in "lr" and tp in "tb":
        pts.append((p2[0], p1[1]))
    elif fp in "tb" and tp in "lr":
        if lane_x is None:
            pts.append((p1[0], p2[1]))
        else:
            step = 16 if fp == "b" else -16
            pts += [(p1[0], p1[1] + step), (lane_x, p1[1] + step), (lane_x, p2[1])]
    else:  # sisi ke sisi
        if lane_x is not None:
            pts += [(lane_x, p1[1]), (lane_x, p2[1])]
        elif abs(p1[1] - p2[1]) > 0.5:
            mid = (p1[0] + p2[0]) / 2
            pts += [(mid, p1[1]), (mid, p2[1])]
    pts.append(p2)
    return pts


# ---------------------------------------------------------------- SVG
def text_lines(x: float, y: float, text: str, color: str, weight: str = "normal") -> str:
    lines = text.split("\n")
    lh = FONT_SIZE * 1.25
    y0 = y - (len(lines) - 1) * lh / 2
    out = []
    for i, line in enumerate(lines):
        out.append(
            f'<text x="{x:.1f}" y="{y0 + i * lh:.1f}" text-anchor="middle" dominant-baseline="central" '
            f'font-family="{FONT}" font-size="{FONT_SIZE}" font-weight="{weight}" fill="{color}">{escape(line)}</text>'
        )
    return "".join(out)


def svg_node(n: Node) -> str:
    x, y, w, h = n.x, n.y, n.w, n.h
    L, T = x - w / 2, y - h / 2
    k = n.kind
    if k == "T":
        shape = f'<rect x="{L}" y="{T}" width="{w}" height="{h}" rx="{h / 2}" fill="{NAVY}" stroke="{NAVY}" stroke-width="1.5"/>'
        return shape + text_lines(x, y, n.text, "#FFFFFF", "bold")
    if k == "P":
        shape = f'<rect x="{L}" y="{T}" width="{w}" height="{h}" fill="{BLUE_FILL}" stroke="{BLUE_LINE}" stroke-width="1.5"/>'
    elif k == "D":
        shape = (
            f'<polygon points="{x},{T} {L + w},{y} {x},{T + h} {L},{y}" '
            f'fill="{TEAL_FILL}" stroke="{TEAL_LINE}" stroke-width="1.5"/>'
        )
    elif k == "IO":
        shape = (
            f'<polygon points="{L + SKEW},{T} {L + w},{T} {L + w - SKEW},{T + h} {L},{T + h}" '
            f'fill="{BLUE_FILL}" stroke="{BLUE_LINE}" stroke-width="1.5"/>'
        )
    elif k == "S":
        shape = (
            f'<rect x="{L}" y="{T}" width="{w}" height="{h}" fill="{BLUE_FILL}" stroke="{BLUE_LINE}" stroke-width="1.5"/>'
            f'<rect x="{L + 5}" y="{T + 5}" width="{w - 10}" height="{h - 10}" fill="none" stroke="{BLUE_LINE}" stroke-width="1.2"/>'
        )
    elif k == "DB":
        ry = 7
        shape = (
            f'<path d="M{L},{T + ry} A{w / 2},{ry} 0 0 1 {L + w},{T + ry} L{L + w},{T + h - ry} '
            f'A{w / 2},{ry} 0 0 1 {L},{T + h - ry} Z" fill="{BLUE_FILL}" stroke="{BLUE_LINE}" stroke-width="1.5"/>'
            f'<path d="M{L},{T + ry} A{w / 2},{ry} 0 0 0 {L + w},{T + ry}" fill="none" stroke="{BLUE_LINE}" stroke-width="1.5"/>'
        )
        return shape + text_lines(x, y + ry / 2, n.text, NAVY)
    elif k == "C":
        shape = f'<circle cx="{x}" cy="{y}" r="{w / 2}" fill="{BLUE_FILL}" stroke="{BLUE_LINE}" stroke-width="1.5"/>'
        return shape + text_lines(x, y, n.text, NAVY, "bold")
    else:
        raise ValueError(k)
    return shape + text_lines(x, y, n.text, NAVY)


def svg_edge(chart: Chart, edge: Edge) -> str:
    pts = route(chart, edge)
    d = " ".join(f"{'M' if i == 0 else 'L'}{px:.1f},{py:.1f}" for i, (px, py) in enumerate(pts))
    out = f'<path d="{d}" fill="none" stroke="{LINE}" stroke-width="1.4" marker-end="url(#arrow)"/>'
    if edge.label:
        (x1, y1), (x2, y2) = pts[0], pts[1]
        if abs(x1 - x2) < 0.5:  # segmen pertama vertikal
            lx, ly, anchor = x1 + 6, y1 + (13 if y2 > y1 else -9), "start"
        elif x2 > x1:
            lx, ly, anchor = x1 + 6, y1 - 7, "start"
        else:
            lx, ly, anchor = x1 - 6, y1 - 7, "end"
        out += (
            f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" font-family="{FONT}" font-size="12" '
            f'font-weight="bold" fill="{LINE}">{escape(edge.label)}</text>'
        )
    return out


def bounds(chart: Chart) -> tuple[float, float, float, float]:
    xs, ys = [], []
    for n in chart.nodes:
        xs += [n.x - n.w / 2, n.x + n.w / 2]
        ys += [n.y - n.h / 2, n.y + n.h / 2]
    for e in chart.edges:
        for px, py in route(chart, e):
            xs.append(px)
            ys.append(py)
    pad = 24
    return min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad


def to_svg(chart: Chart) -> str:
    x0, y0, x1, y1 = bounds(chart)
    w, h = x1 - x0, y1 - y0
    body = "".join(svg_edge(chart, e) for e in chart.edges) + "".join(svg_node(n) for n in chart.nodes)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0:.0f} {y0:.0f} {w:.0f} {h:.0f}" '
        f'width="{w:.0f}" height="{h:.0f}" role="img" aria-label="{escape(chart.title)}">'
        f'<title>{escape(chart.title)}</title>'
        '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" '
        f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{LINE}"/></marker></defs>'
        f'<rect x="{x0:.0f}" y="{y0:.0f}" width="{w:.0f}" height="{h:.0f}" fill="#FFFFFF"/>'
        f"{body}</svg>"
    )


# ---------------------------------------------------------------- draw.io
DRAWIO_STYLE = {
    "T": f"rounded=1;arcSize=50;whiteSpace=wrap;html=1;fillColor={NAVY};strokeColor={NAVY};fontColor=#FFFFFF;fontStyle=1;",
    "P": f"rounded=0;whiteSpace=wrap;html=1;fillColor={BLUE_FILL};strokeColor={BLUE_LINE};fontColor={NAVY};",
    "D": f"rhombus;whiteSpace=wrap;html=1;fillColor={TEAL_FILL};strokeColor={TEAL_LINE};fontColor={NAVY};",
    "IO": f"shape=parallelogram;perimeter=parallelogramPerimeter;fixedSize=1;size={SKEW};whiteSpace=wrap;html=1;fillColor={BLUE_FILL};strokeColor={BLUE_LINE};fontColor={NAVY};",
    "S": f"shape=ext;double=1;rounded=0;whiteSpace=wrap;html=1;fillColor={BLUE_FILL};strokeColor={BLUE_LINE};fontColor={NAVY};",
    "DB": f"shape=cylinder3;boundedLbl=1;backgroundOutline=1;size=7;whiteSpace=wrap;html=1;fillColor={BLUE_FILL};strokeColor={BLUE_LINE};fontColor={NAVY};",
    "C": f"ellipse;aspect=fixed;whiteSpace=wrap;html=1;fillColor={BLUE_FILL};strokeColor={BLUE_LINE};fontColor={NAVY};fontStyle=1;",
}
PORT_XY = {"t": (0.5, 0), "b": (0.5, 1), "l": (0, 0.5), "r": (1, 0.5)}


def drawio_page(chart: Chart, index: int) -> str:
    x0, y0, _, _ = bounds(chart)
    dx, dy = -x0 + 20, -y0 + 20
    cells = ['<mxCell id="0"/>', '<mxCell id="1" parent="0"/>']
    for n in chart.nodes:
        value = escape(n.text).replace("\n", "&lt;br&gt;")
        style = DRAWIO_STYLE[n.kind] + f"fontSize=12;fontFamily=Arial;"
        cells.append(
            f'<mxCell id="p{index}-{n.id}" value="{value}" style="{style}" vertex="1" parent="1">'
            f'<mxGeometry x="{n.x - n.w / 2 + dx:.0f}" y="{n.y - n.h / 2 + dy:.0f}" width="{n.w}" height="{n.h}" as="geometry"/></mxCell>'
        )
    for i, e in enumerate(chart.edges):
        pts = route(chart, e)[1:-1]
        ex, ey = PORT_XY[e.fp]
        nx, ny = PORT_XY[e.tp]
        style = (
            f"edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;endFill=1;strokeColor={LINE};"
            f"exitX={ex};exitY={ey};exitDx=0;exitDy=0;entryX={nx};entryY={ny};entryDx=0;entryDy=0;"
            "fontStyle=1;fontSize=12;labelBackgroundColor=#FFFFFF;"
        )
        points = "".join(f'<mxPoint x="{px + dx:.0f}" y="{py + dy:.0f}"/>' for px, py in pts)
        geom = '<mxGeometry x="-0.7" relative="1" as="geometry">'
        if points:
            geom += f'<Array as="points">{points}</Array>'
        geom += "</mxGeometry>"
        cells.append(
            f'<mxCell id="p{index}-e{i}" value="{escape(e.label or "")}" style="{style}" edge="1" parent="1" '
            f'source="p{index}-{e.a}" target="p{index}-{e.b}">{geom}</mxCell>'
        )
    return (
        f'<diagram id="ems-{index}" name="{escape(chart.title)}"><mxGraphModel grid="1" gridSize="10" '
        f'page="1" pageScale="1" pageWidth="1169" pageHeight="1654"><root>{"".join(cells)}</root></mxGraphModel></diagram>'
    )


# ---------------------------------------------------------------- isi flowchart
def build() -> list[Chart]:
    charts: list[Chart] = []

    # 1. Program utama: acquisition worker ------------------------------------
    c = Chart(
        "01-program-utama-akuisisi",
        "Flowchart Program Utama – Acquisition Worker",
        "Loop utama pembacaan power meter: memuat meter dari database, terhubung ke MQTT, "
        "lalu melakukan polling setiap 5 detik dengan jadwal interval tetap.",
    )
    c.n("start", "T", 1, 0, "MULAI")
    c.n("cfg", "P", 1, 1, "Baca konfigurasi .env\n(mode akuisisi, interval 5 s)")
    c.n("load", "DB", 1, 2, "Muat daftar power meter\naktif dari database")
    c.n("dbok", "D", 1, 3, "Database\nberhasil diakses?")
    c.n("dbwait", "P", 0, 3, "Laporkan error,\ntunggu 5 detik")
    c.n("mqtt", "IO", 1, 4, "Hubungkan ke MQTT broker\n(username & password)")
    c.n("mqok", "D", 1, 5, "Broker\nterhubung?")
    c.n("mqwait", "P", 2, 5, "Laporkan error,\ntunggu 5 detik")
    c.n("cA3", "C", 2, 6, "A")
    c.n("cB", "C", 0, 6, "B")
    c.n("reload", "S", 1, 6, "Muat ulang daftar meter\n(setiap 60 detik)")
    c.n("group", "P", 1, 7, "Kelompokkan meter per\ngateway (host, port)")
    c.n("poll", "S", 1, 8, "Polling semua gateway\nsecara paralel")
    c.n("mqlost", "D", 1, 9, "Koneksi MQTT\nterputus?")
    c.n("close", "P", 2, 9, "Tutup koneksi gateway,\nlaporkan error,\ntunggu 5 detik")
    c.n("cA1", "C", 2, 10, "A")
    c.n("cA2", "C", 2, 2, "A")
    c.n("deadline", "P", 1, 10, "Hitung jadwal siklus berikutnya\n(waktu mulai + 5 detik)")
    c.n("late", "D", 1, 11, "Siklus melebihi\ninterval?")
    c.n("skip", "P", 2, 11, "Lewati siklus terlambat,\ncatat peringatan")
    c.n("sleep", "P", 1, 12, "Tunggu hingga jadwal\nsiklus berikutnya")
    c.n("stop", "D", 1, 13, "Layanan\ndihentikan?")
    c.n("cB2", "C", 0, 13, "B")
    c.n("end", "T", 1, 14, "SELESAI")
    c.e("start", "cfg")
    c.e("cfg", "load")
    c.e("load", "dbok")
    c.e("dbok", "dbwait", "Tidak", "l", "r")
    c.e("dbwait", "load", None, "t", "l")
    c.e("dbok", "mqtt", "Ya")
    c.e("mqtt", "mqok")
    c.e("mqok", "mqwait", "Tidak", "r", "l")
    c.e("mqwait", "cA3")
    c.e("mqok", "reload", "Ya")
    c.e("cB", "reload", None, "r", "l")
    c.e("reload", "group")
    c.e("group", "poll")
    c.e("poll", "mqlost")
    c.e("mqlost", "close", "Ya", "r", "l")
    c.e("close", "cA1")
    c.e("cA2", "load", None, "l", "r")
    c.e("mqlost", "deadline", "Tidak")
    c.e("deadline", "late")
    c.e("late", "skip", "Ya", "r", "l")
    c.e("skip", "sleep", None, "b", "r")
    c.e("late", "sleep", "Tidak")
    c.e("sleep", "stop")
    c.e("stop", "cB2", "Tidak", "l", "r")
    c.e("stop", "end", "Ya")
    charts.append(c)

    # 2. Subrutin polling gateway & meter -------------------------------------
    c = Chart(
        "02-subrutin-polling-meter",
        "Subrutin Polling Gateway dan Power Meter",
        "Dijalankan paralel untuk tiap gateway; meter dalam satu jalur RS485 dibaca berurutan, "
        "hasilnya dipublikasikan ke MQTT.",
    )
    c.n("start", "T", 1, 0, "MULAI\nPolling gateway")
    c.n("next", "P", 1, 1, "Ambil power meter berikutnya\npada gateway (berurutan)")
    c.n("sim", "D", 1, 2, "Mode\nsimulator?")
    c.n("gen", "P", 0, 3, "Bangkitkan telemetry simulasi\n(energi = integrasi daya)")
    c.n("read", "S", 1, 3, "Baca register Modbus\ndan decode")
    c.n("err", "D", 1, 4, "Terjadi error\nbaca / koneksi?")
    c.n("has", "D", 1, 5, "Payload\ntelemetry ada?")
    c.n("off", "IO", 2, 5, "Publish status offline\nke MQTT")
    c.n("log", "P", 2, 6, "Catat meter gagal dibaca\n(log)")
    c.n("tele", "IO", 1, 6, "Publish telemetry ke MQTT\n(QoS 1)")
    c.n("on", "IO", 1, 7, "Publish status online\nke MQTT")
    c.n("more", "D", 1, 8, "Masih ada meter\ndi gateway?")
    c.n("end", "T", 1, 9, "KEMBALI")
    c.e("start", "next")
    c.e("next", "sim")
    c.e("sim", "gen", "Ya", "l", "t")
    c.e("sim", "read", "Tidak")
    c.e("read", "err")
    c.e("err", "off", "Ya", "r", "t")
    c.e("err", "has", "Tidak")
    c.e("gen", "has", None, "b", "l")
    c.e("has", "off", "Tidak", "r", "l")
    c.e("off", "log")
    c.e("has", "tele", "Ya")
    c.e("tele", "on")
    c.e("on", "more")
    c.e("log", "more", None, "b", "r")
    c.e("more", "next", "Ya", "l", "l", lane=-0.62)
    c.e("more", "end", "Tidak")
    charts.append(c)

    # 3. Subrutin baca register Modbus ----------------------------------------
    c = Chart(
        "03-subrutin-baca-modbus",
        "Subrutin Baca Register Modbus dan Decode",
        "Membaca blok register satu meter melalui gateway RS485-to-Ethernet (Modbus TCP) "
        "sesuai profil model, lalu decode dan normalisasi.",
    )
    c.n("start", "T", 1, 0, "MULAI\nBaca meter")
    c.n("alive", "D", 1, 1, "Koneksi gateway\nmasih aktif?")
    c.n("open", "IO", 2, 1, "Buka koneksi Modbus TCP\nke gateway RS485-Ethernet")
    c.n("ok", "D", 2, 2, "Koneksi\nberhasil?")
    c.n("blocks", "P", 1, 2, "Ambil daftar blok register\ndari profil model meter")
    c.n("fc", "D", 1, 3, "Function code\nprofil?")
    c.n("fc3", "IO", 0, 4, "Baca holding register\n(FC03)")
    c.n("fc4", "IO", 2, 4, "Baca input register\n(FC04)")
    c.n("resp", "D", 1, 5, "Respons\nerror?")
    c.n("fail", "P", 3, 5, "Tutup koneksi,\nangkat error")
    c.n("store", "P", 1, 6, "Simpan alamat awal\ndan data word")
    c.n("more", "D", 1, 7, "Masih ada\nblok register?")
    c.n("decode", "P", 1, 8, "Decode register: tipe data,\nskala, dan urutan word")
    c.n("norm", "P", 1, 9, "Normalisasi ke payload telemetry\n(rata-rata fase, waktu UTC)")
    c.n("end", "T", 1, 10, "KEMBALI\npayload")
    c.n("end2", "T", 3, 10, "KEMBALI\nerror")
    c.e("start", "alive")
    c.e("alive", "open", "Tidak", "r", "l")
    c.e("open", "ok")
    c.e("ok", "blocks", "Ya", "l", "r")
    c.e("ok", "fail", "Tidak", "r", "t")
    c.e("alive", "blocks", "Ya")
    c.e("blocks", "fc")
    c.e("fc", "fc3", "FC03", "l", "t")
    c.e("fc", "fc4", "FC04", "r", "t")
    c.e("fc3", "resp")
    c.e("fc4", "resp")
    c.e("resp", "fail", "Ya", "r", "l")
    c.e("resp", "store", "Tidak")
    c.e("store", "more")
    c.e("more", "fc", "Ya", "l", "t", via=[(-0.62, 7), (-0.62, 2.58), (1, 2.58)])
    c.e("more", "decode", "Tidak")
    c.e("decode", "norm")
    c.e("norm", "end")
    c.e("fail", "end2")
    charts.append(c)

    # 4. Program backend: MQTT subscriber -------------------------------------
    c = Chart(
        "04-program-backend-mqtt",
        "Flowchart Program Backend – Penerimaan Data MQTT",
        "Backend FastAPI menjalankan task latar (MQTT subscriber dan offline watcher) sambil melayani "
        "REST API dan WebSocket.",
    )
    c.n("start", "T", 1, 0, "MULAI\nBackend API")
    c.n("tasks", "P", 1, 1, "Jalankan task latar\ndan server HTTP")
    c.n("rest", "S", 0, 1, "Layani REST API\n& WebSocket /ws")
    c.n("watch", "S", 2, 1, "Offline watcher\n(setiap 15 detik)")
    c.n("conn", "IO", 1, 2, "Hubungkan ke MQTT broker &\nsubscribe ems/meter/+/telemetry")
    c.n("ok", "D", 1, 3, "Terhubung?")
    c.n("wait", "IO", 0, 3, "Laporkan error ke Telegram,\ntunggu 5 detik")
    c.n("cA", "C", 0, 4, "A")
    c.n("recv", "IO", 1, 4, "Terima pesan telemetry\ndari MQTT")
    c.n("json", "D", 1, 5, "Payload JSON\nvalid?")
    c.n("bad", "IO", 2, 5, "Laporkan payload tidak\nvalid (Telegram)")
    c.n("cA3", "C", 2, 6, "A")
    c.n("ingest", "S", 1, 6, "Ingest telemetry\n(simpan & broadcast)")
    c.n("saved", "D", 1, 7, "Penyimpanan\nberhasil?")
    c.n("dberr", "IO", 2, 7, "Laporkan error database\n(Telegram)")
    c.n("lost", "D", 1, 8, "Koneksi MQTT\nterputus?")
    c.n("stop", "D", 1, 9, "Layanan\ndihentikan?")
    c.n("cA2", "C", 0, 9, "A")
    c.n("end", "T", 1, 10, "SELESAI")
    c.e("start", "tasks")
    c.e("tasks", "rest", None, "l", "r")
    c.e("tasks", "watch", None, "r", "l")
    c.e("tasks", "conn")
    c.e("conn", "ok")
    c.e("ok", "wait", "Tidak", "l", "r")
    c.e("wait", "conn", None, "t", "l")
    c.e("ok", "recv", "Ya")
    c.e("cA", "recv", None, "r", "l")
    c.e("recv", "json")
    c.e("json", "bad", "Tidak", "r", "l")
    c.e("bad", "cA3")
    c.e("json", "ingest", "Ya")
    c.e("ingest", "saved")
    c.e("saved", "dberr", "Tidak", "r", "l")
    c.e("dberr", "lost", None, "b", "r")
    c.e("saved", "lost", "Ya")
    c.e("lost", "wait", "Ya", "l", "l", lane=-0.62)
    c.e("lost", "stop", "Tidak")
    c.e("stop", "cA2", "Tidak", "l", "r")
    c.e("stop", "end", "Ya")
    charts.append(c)

    # 5. Subrutin ingest telemetry --------------------------------------------
    c = Chart(
        "05-subrutin-ingest-telemetry",
        "Subrutin Ingest Telemetry",
        "Memvalidasi meter, menghitung nilai turunan (PF, kVAh), menyimpan ke PostgreSQL/TimescaleDB, "
        "mengevaluasi alarm, lalu menyiarkan data ke dashboard.",
    )
    c.n("start", "T", 1, 0, "MULAI\nIngest telemetry")
    c.n("code", "D", 1, 1, "device_code\nada?")
    c.n("find", "DB", 1, 2, "Cari meter berdasarkan\ndevice_code")
    c.n("known", "D", 1, 3, "Meter\nterdaftar?")
    c.n("ignore", "T", 2, 3, "KEMBALI\n(diabaikan)")
    c.n("ts", "P", 1, 4, "Parse timestamp\n(kosong → waktu sekarang UTC)")
    c.n("prev", "DB", 1, 5, "Ambil pembacaan sebelumnya\n(kWh, kVAh, PF)")
    c.n("calc", "P", 1, 6, "Hitung PF = |P / S|,\nkVAh += ΔkWh / PF rata-rata")
    c.n("cA", "C", 1, 7, "A")
    c.n("cA2", "C", 3, 0, "A")
    c.n("save", "DB", 3, 1, "Simpan readings & phase_readings\n(abaikan data duplikat)")
    c.n("seen", "P", 3, 2, "Perbarui last_seen_at,\nhapus alarm offline terbuka")
    c.n("alarm", "S", 3, 3, "Evaluasi alarm\n(delay & hysteresis)")
    c.n("commit", "DB", 3, 4, "Commit transaksi\ndatabase")
    c.n("notify", "IO", 3, 5, "Kirim notifikasi alarm kritis\n/ pulih ke Telegram")
    c.n("snap", "P", 3, 6, "Simpan snapshot & status\nmeter terbaru di Hub")
    c.n("ws", "IO", 3, 7, "Broadcast telemetry ke semua\nklien WebSocket")
    c.n("end", "T", 3, 8, "KEMBALI")
    c.e("start", "code")
    c.e("code", "ignore", "Tidak", "r", "t")
    c.e("code", "find", "Ya")
    c.e("find", "known")
    c.e("known", "ignore", "Tidak", "r", "l")
    c.e("known", "ts", "Ya")
    c.e("ts", "prev")
    c.e("prev", "calc")
    c.e("calc", "cA")
    for a, b in [("cA2", "save"), ("save", "seen"), ("seen", "alarm"), ("alarm", "commit"),
                 ("commit", "notify"), ("notify", "snap"), ("snap", "ws"), ("ws", "end")]:
        c.e(a, b)
    charts.append(c)

    # 6. Subrutin evaluasi alarm ----------------------------------------------
    c = Chart(
        "06-subrutin-evaluasi-alarm",
        "Subrutin Evaluasi Alarm",
        "Alarm dibuat bila kondisi abnormal bertahan ≥ 30 detik dan dinyatakan normal bila kondisi "
        "normal (di luar deadband) bertahan ≥ 30 detik.",
    )
    c.n("start", "T", 1, 0, "MULAI\nEvaluasi alarm")
    c.n("check", "P", 1, 1, "Periksa PF, tegangan, frekuensi,\nTHD-I, unbalance, dan beban")
    c.n("open", "DB", 1, 2, "Ambil alarm terbuka\nmilik meter")
    c.n("next", "P", 1, 3, "Ambil jenis alarm berikutnya\n(terbuka atau abnormal)")
    c.n("isopen", "D", 1, 4, "Alarm jenis ini\nsudah terbuka?")
    c.n("still", "D", 2, 5, "Masih abnormal\n(dalam deadband)?")
    c.n("upd", "P", 3, 5, "Perbarui severity\ndan pesan alarm")
    c.n("normal", "D", 2, 6, "Normal\n≥ 30 detik?")
    c.n("clear", "DB", 2, 7, "Tandai alarm\ncleared")
    c.n("pend", "D", 1, 5, "Abnormal\n≥ 30 detik?")
    c.n("create", "DB", 1, 6, "Buat alarm baru\n(severity & pesan)")
    c.n("more", "D", 1, 8, "Masih ada\njenis alarm?")
    c.n("new", "D", 1, 9, "Ada alarm\nbaru?")
    c.n("bc", "IO", 2, 9, "Broadcast alarm baru\nke WebSocket")
    c.n("notice", "P", 1, 10, "Susun notifikasi: kritis → laporan,\nnormal / turun → pulih")
    c.n("end", "T", 1, 11, "KEMBALI")
    c.e("start", "check")
    c.e("check", "open")
    c.e("open", "next")
    c.e("next", "isopen")
    c.e("isopen", "still", "Ya", "r", "t")
    c.e("isopen", "pend", "Tidak")
    c.e("still", "upd", "Ya", "r", "l")
    c.e("still", "normal", "Tidak")
    c.e("normal", "clear", "Ya")
    c.e("normal", "more", "Tidak", "r", "r", lane=3.0)
    c.e("upd", "more", None, "b", "r")
    c.e("clear", "more", None, "b", "r")
    c.e("pend", "create", "Ya")
    c.e("pend", "more", "Tidak", "l", "t", via=[(0.25, 5), (0.25, 7.45), (1, 7.45)])
    c.e("create", "more")
    c.e("more", "next", "Ya", "l", "l", lane=-0.1)
    c.e("more", "new", "Tidak")
    c.e("new", "bc", "Ya", "r", "l")
    c.e("bc", "notice", None, "b", "r")
    c.e("new", "notice", "Tidak")
    c.e("notice", "end")
    charts.append(c)

    # 7. Subrutin offline watcher ---------------------------------------------
    c = Chart(
        "07-subrutin-offline-watcher",
        "Subrutin Offline Watcher",
        "Memeriksa umur data setiap meter setiap 15 detik: > 30 detik warning, > 180 detik critical "
        "dan dikirim notifikasi Telegram.",
    )
    c.n("start", "T", 1, 0, "MULAI\nOffline watcher")
    c.n("sleep", "P", 1, 1, "Tunggu 15 detik")
    c.n("load", "DB", 1, 2, "Ambil daftar power meter aktif")
    c.n("next", "P", 1, 3, "Ambil meter berikutnya")
    c.n("never", "D", 1, 4, "last_seen_at\nkosong?")
    c.n("crit", "P", 2, 5, "Set alarm offline\nCRITICAL")
    c.n("mark", "P", 3, 5, "Tandai untuk notifikasi\nTelegram")
    c.n("age", "P", 1, 5, "Hitung umur data =\nsekarang − last_seen_at")
    c.n("gt180", "D", 1, 6, "Umur > 180\ndetik?")
    c.n("gt30", "D", 1, 7, "Umur > 30\ndetik?")
    c.n("warn", "P", 2, 7, "Set alarm offline\nWARNING")
    c.n("more", "D", 1, 8, "Masih ada\nmeter?")
    c.n("commit", "DB", 1, 9, "Commit perubahan alarm")
    c.n("tg", "IO", 1, 10, "Kirim notifikasi meter\noffline ke Telegram")
    c.n("stop", "D", 1, 11, "Layanan\ndihentikan?")
    c.n("end", "T", 1, 12, "SELESAI")
    c.e("start", "sleep")
    c.e("sleep", "load")
    c.e("load", "next")
    c.e("next", "never")
    c.e("never", "crit", "Ya", "r", "t")
    c.e("never", "age", "Tidak")
    c.e("age", "gt180")
    c.e("gt180", "crit", "Ya", "r", "b")
    c.e("gt180", "gt30", "Tidak")
    c.e("crit", "mark", None, "r", "l")
    c.e("mark", "more", None, "b", "r")
    c.e("gt30", "warn", "Ya", "r", "l")
    c.e("warn", "more", None, "b", "r")
    c.e("gt30", "more", "Tidak")
    c.e("more", "next", "Ya", "l", "l", lane=-0.62)
    c.e("more", "commit", "Tidak")
    c.e("commit", "tg")
    c.e("tg", "stop")
    c.e("stop", "sleep", "Tidak", "r", "r", lane=3.6)
    c.e("stop", "end", "Ya")
    charts.append(c)

    # 8. Program frontend dashboard -------------------------------------------
    c = Chart(
        "08-program-frontend-dashboard",
        "Flowchart Program Frontend – Dashboard",
        "Dashboard Next.js memuat data lewat REST, lalu memperbarui tampilan secara realtime lewat "
        "WebSocket dengan sinkronisasi REST berkala setiap 60 detik.",
    )
    c.n("start", "T", 1, 0, "MULAI\nBuka dashboard")
    c.n("fetch", "IO", 1, 1, "Ambil data meter & ringkasan\n(GET /api/devices, /api/summary)")
    c.n("ok", "D", 1, 2, "Request\nberhasil?")
    c.n("has", "D", 1, 3, "Data meter\ntersedia?")
    c.n("demo", "D", 2, 3, "Mode demo\naktif?")
    c.n("sim", "P", 3, 3, "Tampilkan data simulasi\n+ tanda Mode demo")
    c.n("errm", "IO", 2, 4, "Tampilkan pesan error\n(tanpa angka palsu)")
    c.n("show", "IO", 1, 4, "Tampilkan KPI, grafik,\ndan status meter")
    c.n("ws", "IO", 1, 5, "Hubungkan WebSocket /ws")
    c.n("wsok", "D", 1, 6, "WebSocket\nterhubung?")
    c.n("retry", "P", 0, 6, "Tunggu 3 detik,\nhubungkan ulang")
    c.n("recv", "IO", 1, 7, "Terima pesan realtime\n(snapshot / telemetry / alarm)")
    c.n("type", "D", 1, 8, "Jenis pesan\nalarm?")
    c.n("cA1", "C", 2, 8, "A")
    c.n("queue", "P", 1, 9, "Antrekan pesan per meter,\nterapkan tiap 1 detik")
    c.n("newdev", "D", 1, 10, "Ada meter\nbaru?")
    c.n("cA2", "C", 2, 10, "A")
    c.n("update", "IO", 1, 11, "Perbarui tampilan realtime\n(daya, tegangan, status)")
    c.n("sync", "D", 1, 12, "Sudah 60 detik\nsejak sinkron?")
    c.n("cA3", "C", 2, 12, "A")
    c.n("close", "D", 1, 13, "Halaman\nditutup?")
    c.n("cB", "C", 0, 13, "B")
    c.n("cB2", "C", 0, 7, "B")
    c.n("cA4", "C", 3, 8, "A")
    c.n("resync", "IO", 3, 9, "Sinkron ulang data via REST\n(GET devices & summary)")
    c.n("cB3", "C", 3, 10, "B")
    c.n("end", "T", 1, 14, "SELESAI")
    c.e("start", "fetch")
    c.e("cA4", "resync")
    c.e("resync", "cB3")
    c.e("cB2", "recv", None, "r", "l")
    c.e("fetch", "ok")
    c.e("ok", "demo", "Tidak", "r", "t")
    c.e("ok", "has", "Ya")
    c.e("has", "demo", "Tidak", "r", "l")
    c.e("has", "show", "Ya")
    c.e("demo", "sim", "Ya", "r", "l")
    c.e("demo", "errm", "Tidak")
    c.e("sim", "ws", None, "b", "r")
    c.e("errm", "ws", None, "b", "r")
    c.e("show", "ws")
    c.e("ws", "wsok")
    c.e("wsok", "retry", "Tidak", "l", "r")
    c.e("retry", "ws", None, "t", "l")
    c.e("wsok", "recv", "Ya")
    c.e("recv", "type")
    c.e("type", "cA1", "Ya", "r", "l")
    c.e("type", "queue", "Tidak")
    c.e("queue", "newdev")
    c.e("newdev", "cA2", "Ya", "r", "l")
    c.e("newdev", "update", "Tidak")
    c.e("update", "sync")
    c.e("sync", "cA3", "Ya", "r", "l")
    c.e("sync", "close", "Tidak")
    c.e("close", "cB", "Tidak", "l", "r")
    c.e("close", "end", "Ya")
    charts.append(c)

    return charts


# ---------------------------------------------------------------- legenda & HTML
LEGEND = [
    ("T", "Terminator", "Awal (MULAI) dan akhir (SELESAI) program"),
    ("P", "Proses", "Operasi, perhitungan, atau penugasan variabel"),
    ("D", "Keputusan", "Percabangan Ya/Tidak berdasarkan kondisi"),
    ("IO", "Input / Output", "Membaca sensor, menerima atau mengirim data"),
    ("S", "Subrutin", "Memanggil fungsi / modul yang dirinci terpisah"),
    ("DB", "Penyimpanan data", "Akses database atau memori"),
    ("C", "Konektor", "Sambungan antarhalaman / antarbagian flowchart"),
]


def legend_svg(kind: str) -> str:
    n = Node("x", kind, 0, 0, "A" if kind == "C" else "")
    pad = 6
    w, h = n.w + 2 * pad, n.h + 2 * pad
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{-w / 2} {-h / 2} {w} {h}" width="{w * 0.55:.0f}" '
        f'height="{h * 0.55:.0f}">{svg_node(n)}</svg>'
    )


def build_html(charts: list[Chart]) -> str:
    rows = "".join(
        f"<tr><td>{i}</td><td class='sym'>{legend_svg(k)}</td><td>{name}</td><td>{fn}</td></tr>"
        for i, (k, name, fn) in enumerate(LEGEND, 1)
    )
    toc = "".join(f'<li><a href="#{c.slug}">{escape(c.title)}</a></li>' for c in charts)
    sections = "".join(
        f'<section id="{c.slug}"><h2>{i}. {escape(c.title)}</h2><p>{escape(c.desc)}</p>'
        f'<div class="fig">{to_svg(c)}</div><p class="file">File: <a href="{c.slug}.svg">{c.slug}.svg</a></p></section>'
        for i, c in enumerate(charts, 1)
    )
    return f"""<!doctype html>
<html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Flowchart Program EMS</title>
<style>
:root{{--bg:#F5F7FA;--card:#FFFFFF;--ink:#16263A;--muted:#5A6B7D;--line:#D6DEE8;--accent:{NAVY}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 {FONT}}}
main{{max-width:1100px;margin:0 auto;padding:32px 16px 64px}}
h1{{font-size:26px;margin:0 0 6px;color:var(--accent)}}
h2{{font-size:19px;margin:0 0 4px;color:var(--accent)}}
p{{margin:0 0 12px;color:var(--muted)}}
section,.card{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:20px;margin-top:20px}}
table{{border-collapse:collapse;width:100%}}
td,th{{border:1px solid var(--line);padding:6px 10px;text-align:left;vertical-align:middle}}
th{{background:#EEF3F9}}
td.sym{{text-align:center;width:120px}}
.fig{{overflow-x:auto;text-align:center}}
.fig svg{{max-width:100%;height:auto}}
.file{{font-size:13px;margin-top:8px}}
ol{{margin:0;padding-left:20px}}
a{{color:var(--accent)}}
</style></head><body><main>
<h1>Flowchart Program Energy Monitoring System</h1>
<p>Disusun dari implementasi kode: acquisition worker (Python + pymodbus), backend FastAPI, MQTT Mosquitto,
PostgreSQL/TimescaleDB, dan dashboard Next.js.</p>
<div class="card"><h2>Keterangan simbol</h2>
<table><thead><tr><th>No</th><th>Simbol</th><th>Nama</th><th>Fungsi</th></tr></thead><tbody>{rows}</tbody></table></div>
<div class="card"><h2>Daftar flowchart</h2><ol>{toc}</ol></div>
{sections}
</main></body></html>
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    charts = build()
    for c in charts:
        (OUT / f"{c.slug}.svg").write_text(to_svg(c), encoding="utf-8")
    pages = "".join(drawio_page(c, i) for i, c in enumerate(charts, 1))
    (OUT / "flowchart-ems.drawio").write_text(
        f'<mxfile host="app.diagrams.net" type="device">{pages}</mxfile>', encoding="utf-8"
    )
    (OUT / "index.html").write_text(build_html(charts), encoding="utf-8")
    print(f"{len(charts)} flowchart ditulis ke {OUT}")


if __name__ == "__main__":
    main()
