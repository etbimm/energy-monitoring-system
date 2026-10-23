# Tabel Register & Skala Power Meter

> Acuan parsing Node-RED. Versi mesin-readable: [`meter-profiles.js`](./meter-profiles.js)
> Dokumentasi lengkap: [`../docs/parameter-specification.md`](../docs/parameter-specification.md)

**PENTING — konfirmasi ke manual alat sebelum commissioning.** Alamat register di bawah
mengikuti konvensi umum **input register (FC 04/FC 03) dengan alamat 0-based**
(`Artifact Address = 40001 + addr`). Sebagian vendor menomori dengan cara berbeda,
jadi cocokkan dengan manual atau fitur "scan register" pada alat.

---

## Ringkasan kapabilitas

| Parameter | PAC3220 | DMG510 | Elite440 | AMC96 | EM220 |
|---|:--:|:--:|:--:|:--:|:--:|
| V (volt) | ✅ | ✅ | ✅ | ✅ | ✅ |
| I (ampere) | ✅ | ✅ | ✅ | ✅ | ✅ |
| kW (daya aktif) | ✅ | ✅ | ✅ | ✅ | ✅ |
| kVA (daya semu) | ✅ | ✅ | ✅ | ✅ | ✅ |
| kVAR (daya reaktif) | ✅ | ✅ | ✅ | ✅ | ✅ |
| kWh (energi aktif) | ✅ | ✅ | ✅ | ✅ | ✅ |
| **kVAh (energi semu)** | ✅ **native** | ❌ | ❌ | ❌ | ❌ |
| kVARh (energi reaktif) | ✅ | ✅ | ✅ | ✅ | ✅ |
| **THD-i (THD arus)** | ✅ | ✅ | ✅ | ⚠️ opsi `/H` | ❌ |
| THD-u (THD tegangan) | ✅ | ✅ | ✅ | ⚠️ opsi `/H` | ❌ |
| Unbalance V / I | ✅ | ❌ | ❌ | ❌ | ❌ |
| PF | ✅ | ✅ | ✅ | ✅ | ✅ |
| Hz | ✅ | ✅ | ✅ | ✅ | ✅ |
| Demand | ✅ | ✅ | ✅ | ❌ | ✅ |
| Per fasa (L1/L2/L3) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Orde harmonik maks | 40 | 15 | 31 | 31 | — |

Jumlah unit: PAC3220 ×5, DMG510 ×3, Elite440 ×1, AMC96 ×6, EM220 ×3 — **total 18**.

---

## ⚠️ Jebakan skala yang paling sering salah

| Jebakan | Gejala | Pencegahan |
|---|---|---|
| Skala integer berbeda per model | Daya 118,6 kW tampil jadi 11,86 kW atau 1186 kW | Selalu pakai `scale` dari `meter-profiles.js`, jangan asumsikan |
| Float vs integer | PAC3220 & Elite440 = **IEEE754 float** | Jangan `parseInt` nilai float |
| Register 32-bit terbelah | kWh melompat / negatif | Baca 2 register, gabung little-endian |
| kVAh dibaca dari meter | Selalu 0 / error | Hitung di backend: `kVAh = kWh / PF` |
| PF dibaca terpisah | Tidak konsisten dengan kW & kVA | Hitung di backend: `PF = kW / kVA` |
| Energy dipoll tiap detik | Register overflow & beban Modbus | Poll 1 menit, ambil delta |

---

## 1. SIEMENS PAC3220 — LVMDP Incoming (5 unit)

Manual: `SENTRON PAC3120 and PAC3220, L1V30425208F_RS-AA_002, 07/2024`

| Label | Addr | Reg | Tipe | Skala | Satuan |
|---|---:|---:|---|---:|---|
| U L1-L2 | 800 | 1 | uint16 | 10 | V |
| U L2-L3 | 801 | 1 | uint16 | 10 | V |
| U L3-L1 | 802 | 1 | uint16 | 10 | V |
| I L1 | 805 | 1 | uint16 | 100 | A |
| I L2 | 806 | 1 | uint16 | 100 | A |
| I L3 | 807 | 1 | uint16 | 100 | A |
| **P total** | 850 | 2 | **float32** | 1 | kW |
| **Q total** | 852 | 2 | **float32** | 1 | kVAR |
| **S total** | 854 | 2 | **float32** | 1 | kVA |
| PF total | 856 | 2 | float32 | 1 | – |
| Frekuensi | 860 | 2 | float32 | 1 | Hz |
| THD I L1 | 870 | 2 | float32 | 1 | % |
| THD I L2 | 872 | 2 | float32 | 1 | % |
| THD I L3 | 874 | 2 | float32 | 1 | % |
| THD U L1 | 876 | 2 | float32 | 1 | % |
| THD U L2 | 878 | 2 | float32 | 1 | % |
| THD U L3 | 880 | 2 | float32 | 1 | % |
| Unbalance U | 884 | 2 | float32 | 1 | % |
| Unbalance I | 886 | 2 | float32 | 1 | % |
| Active energy import T1 | 900 | 2 | uint32 | 100 | kWh |
| Reactive energy import T1 | 902 | 2 | uint32 | 100 | kVARh |
| **Apparent energy T1** | 904 | 2 | uint32 | 100 | **kVAh** |

- Default: 19200 baud, 8N1, FC 04.
- **PAC3220 punya 2 port Ethernet bawaan.** RS485 hanya lewat expansion module — cek
  kondisi实际 di panel, jangan asumsikan semua meter di RS485.
- Twin meter: interval 1–60 menit, bisa 1 menit untuk polling.
- **Satu-satunya model yang punya register kVAh native.**

---

## 2. LOVATO DMG510 — LVMDP Outcoming (3 unit)

Manual: `Digital Multimeter DMG500-DMG510, 604 GB I 09 19`

| Label | Addr | Reg | Tipe | Skala | Satuan |
|---|---:|---:|---|---:|---|
| V L1 | 3000 | 1 | uint16 | 10 | V |
| V L2 | 3001 | 1 | uint16 | 10 | V |
| V L3 | 3002 | 1 | uint16 | 10 | V |
| I L1 | 3003 | 1 | uint16 | 100 | A |
| I L2 | 3004 | 1 | uint16 | 100 | A |
| I L3 | 3005 | 1 | uint16 | 100 | A |
| P aktif | 3006 | 2 | int32 | 100 | kW |
| Q reaktif | 3008 | 2 | int32 | 100 | kVAR |
| S semu | 3010 | 2 | int32 | 100 | kVA |
| PF | 3012 | 1 | int16 | 1000 | – |
| Frekuensi | 3013 | 1 | uint16 | 10 | Hz |
| **THD I L1** | 3100 | 1 | uint16 | 10 | % |
| THD U L1 | 3101 | 1 | uint16 | 10 | % |
| Active energy import | 3200 | 2 | uint32 | 100 | kWh |
| Reactive energy import | 3202 | 2 | uint32 | 100 | kVARh |

- Default: 9600 baud, 8N1, FC 03.
- **THD hanya aktif bila parameter `P02.12 = THD+HAR`** (bukan `THD`).
  Kalau nilainya `THD`, harmonik detail tidak ditampilkan.
- Harmonik sampai **orde 15**.
- Terminal RS485: `A`, `B`, `COM` (GND). Maks 32 unit / 1200 m.
- Tidak punya kVAh.

---

## 3. CEWE Elite440 — MVMDP (1 unit)

Datasheet: `CEWE Elite 440, 7-18/Nov 21`

| Label | Addr | Reg | Tipe | Skala | Satuan |
|---|---:|---:|---|---:|---|
| U L1 | 0 | 2 | float32 | 1 | V |
| U L2 | 2 | 2 | float32 | 1 | V |
| U L3 | 4 | 2 | float32 | 1 | V |
| I L1 | 6 | 2 | float32 | 1 | A |
| I L2 | 8 | 2 | float32 | 1 | A |
| I L3 | 10 | 2 | float32 | 1 | A |
| P aktif | 12 | 2 | float32 | 1 | kW |
| Q reaktif | 14 | 2 | float32 | 1 | kVAR |
| S semu | 16 | 2 | float32 | 1 | kVA |
| PF | 18 | 2 | float32 | 1 | – |
| Frekuensi | 20 | 2 | float32 | 1 | Hz |
| **THD I L1** | 22 | 2 | float32 | 1 | % |
| THD U L1 | 24 | 2 | float32 | 1 | % |
| THD P L1 | 26 | 2 | float32 | 1 | % |
| Active energy import | 40 | 2 | uint32 | 1 | kWh |
| Reactive energy import | 42 | 2 | uint32 | 1 | kVARh |

- Default: 9600 baud, 8N1, FC 03, **data float IEEE754**.
- Meter **multi-line**: register dipetakan per baris (L1/L2/L3) lewat konfigurasi
  di alat, bukan alamat berbeda.
- THD rata-rata untuk tegangan, arus, **dan daya** s/d orde 31.
- Load survey: 40 hari × 6 parameter, interval 30 menit.
- Akurasi kelas 0,2s / 0,5s / 1,0.
- Tidak punya kVAh.

---

## 4. ACREL AMC96 — MCC 1, 2, 3, 4 (6 unit)

Datasheet: `Acrel AMC96L-E4, AMC Series Programmable Power Meter`

| Label | Addr | Reg | Tipe | Skala | Satuan |
|---|---:|---:|---|---:|---|
| U L1 | 0 | 1 | uint16 | 10 | V |
| U L2 | 1 | 1 | uint16 | 10 | V |
| U L3 | 2 | 1 | uint16 | 10 | V |
| I L1 | 3 | 1 | uint16 | 100 | A |
| I L2 | 4 | 1 | uint16 | 100 | A |
| I L3 | 5 | 1 | uint16 | 100 | A |
| P aktif | 6 | 1 | uint16 | 10 | kW |
| Q reaktif | 7 | 1 | uint16 | 10 | kVAR |
| S semu | 8 | 1 | uint16 | 10 | kVA |
| PF | 9 | 1 | uint16 | 100 | – |
| Frekuensi | 10 | 1 | uint16 | 10 | Hz |
| **THD I** *(opsi `/H`)* | 11 | 1 | uint16 | 10 | % |
| THD U *(opsi `/H`)* | 12 | 1 | uint16 | 10 | % |
| Active energy import | 30 | 2 | uint32 | 100 | kWh |
| Reactive energy import | 32 | 2 | uint32 | 100 | kVARh |

- Default: 9600 baud, 8N1, FC 03.
- **THD (register 11–12) hanya ada bila opsi peripheral `/H` terpasang.**
  Tanpa `/H`, register tersebut tidak ada / mengembalikan 0.
  **Verifikasi fisik setiap unit saat commissioning** — lihat port `/H` di belakang alat.
  Data harmonik orde 2–31 dengan akurasi ±1%.
- Akurasi: I/V class 0,2; kW class 1,0; kVARh class 1,0; Hz 0,05.
- Pulse output: 10000/40000/160000 imp/kWh.
- Tidak punya kVAh.

---

## 5. WEIDMULLER EM220 — MCC Pellet 1, 2, 3 (3 unit)

Datasheet: `EM220-RTU-4DI2DO, BasicLine, creation 25.02.2026`

| Label | Addr | Reg | Tipe | Skala | Satuan |
|---|---:|---:|---|---:|---|
| U L1 | 0 | 1 | uint16 | 10 | V |
| U L2 | 1 | 1 | uint16 | 10 | V |
| U L3 | 2 | 1 | uint16 | 10 | V |
| I L1 | 3 | 1 | uint16 | 100 | A |
| I L2 | 4 | 1 | uint16 | 100 | A |
| I L3 | 5 | 1 | uint16 | 100 | A |
| P aktif | 6 | 2 | uint32 | 1000 | kW |
| Q reaktif | 8 | 2 | int32 | 1000 | kVAR |
| S semu | 10 | 2 | uint32 | 1000 | kVA |
| PF | 12 | 1 | int16 | 1000 | – |
| Frekuensi | 13 | 1 | uint16 | 100 | Hz |
| Active energy import | 20 | 2 | uint32 | 100 | kWh |
| Reactive energy import | 22 | 2 | uint32 | 100 | kVARh |
| Active energy export | 24 | 2 | uint32 | 100 | kWh |
| Reactive energy export | 26 | 2 | uint32 | 100 | kVARh |

- Default: 9600 baud, 8N1, FC 03.
- **Meter BasicLine — tanpa analisis harmonik sama sekali.** THD tidak bisa diambil.
- Punya **import dan export** (4 kuadran) untuk energi aktif & reaktif.
- Update interval register internal **1 detik**; polling lebih cepat dari 5 detik sia-sia.
- Akurasi: active energy class 0,5S (IEC 62053-22), reactive class 0,5;
  tegangan & arus 0,5%.
- Terminal: `V1 V2 V3 VN` (voltase), `I1 I2 I3` (CT sekunder 1 A / 5 A),
  `RS485` (A, B), `AUX` (100–240 VAC / 100–380 VDC), 4 DI, 2 DO.
- Tidak punya kVAh.

---

## Mapping device → model

| Device ID | Nama | Tempat | Model |
|---|---|---|---|
| PM-LVMDP-IN-01…05 | LVMDP Incoming 1–5 | LVMDP | SIEMENS PAC3220 |
| PM-LVMDP-OUT-01…03 | LVMDP Outcoming 1–3 | LVMDP | LOVATO DMG510 |
| PM-MVMDP-01 | MVMDP | MVMDP | CEWE Elite440 |
| PM-MCC1-01…02 | MCC 1 Meter 1–2 | MCC 1 | ACREL AMC96 |
| PM-MCC2-01 | MCC 2 Meter 1 | MCC 2 | ACREL AMC96 |
| PM-MCC3-01…02 | MCC 3 Meter 1–2 | MCC 3 | ACREL AMC96 |
| PM-MCC4-01 | MCC 4 Meter 1 | MCC 4 | ACREL AMC96 |
| PM-PEL1-01 | MCC Pellet 1 | MCC Pellet 1 | WEIDMULLER EM220 |
| PM-PEL2-01 | MCC Pellet 2 | MCC Pellet 2 | WEIDMULLER EM220 |
| PM-PEL3-01 | MCC Pellet 3 | MCC Pellet 3 | WEIDMULLER EM220 |

---

## Topologi & segmentasi RS485

- Batas **1.200 m** dan **32 unit per segment** RS485.
- 18 meter + kondisi (arus) pada 1 segment = 1.800 m. Kalau lebih dari 1.200 m,
  wajib dipecah jadi ≥2 segment dengan RS485-to-Ethernet converter per segment.
- **PAC3220 (5 unit di LVMDP) connect langsung via Ethernet** — tidak lewat converter.
- Elite440 & meter lain: pastikan terminating resistor 120 Ω di ujung bus,
  dan shielded twisted pair.

### Checklist commissioning

- [ ] Konfirmasi slave ID tiap meter (default 1 — **wajib diubah** agar tidak bentrok)
- [ ] Konfirmasi baud/parity/stop bit tiap model
- [ ] Verifikasi register kW: bandingkan dengan display panel / clamp meter
- [ ] Verifikasi register kWh: bandingkan dengan pembaca Counter watt-hour
- [ ] **Cek keberadaan opsi `/H` pada 6 unit AMC96** (untuk THD)
- [ ] Pastikan setting `P02.12 = THD+HAR` pada 3 unit DMG510 (untuk THD)
- [ ] Hitung manual PF dari kW & kVA, bandingkan dengan register PF
- [ ] Cek multiplier CT (CT 100/5 = 20) terpasang benar di alat
- [ ] Uji bus saat beban puncak (jarak + noise motor pelletizer)
