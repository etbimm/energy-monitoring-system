# Spesifikasi Parameter & Tabel Register Power Meter

**Proyek:** Java Wood Pellet — Energy Monitoring System
**Versi:** 1.0
**Tanggal:** 21 Oktober 2026
**Status:** acuan parsing Node-RED + kontrak data frontend & backend

---

## 1. Tujuan dokumen

Dokumen ini adalah **sumber kebenaran tunggal** untuk:

1. Daftar parameter yang diambil dari setiap power meter
2. Pemisahan parameter **inti / turunan / opsional** beserta alasannya
3. Matriks kapabilitas per model meter (dari datasheet aktual)
4. Skema tabel database dan kontrak payload
5. Strategi sampling & penyimpanan
6. Jebakan teknis parsing yang harus diwaspai saat commissioning

Dokumen terkait:
- [`../node-red/register-map.md`](../node-red/register-map.md) — tabel register ringkas untuk lapangan
- [`../node-red/meter-profiles.js`](../node-red/meter-profiles.js) — profil register versi mesin-readable
- [`data-model.md`](./data-model.md) — skema tabel
- [`architecture.md`](./architecture.md) — alur data end-to-end

---

## 2. Inventaris power meter

18 unit, 5 model berbeda, 9 titik instalasi.

| No | Tempat | Merk / Model | Jumlah | Peran | Bus | Device ID |
|---:|---|---|---:|---|---|---|
| 1 | LVMDP | SIEMENS PAC3220 (Incoming) | 5 | incoming | Ethernet | PM-LVMDP-IN-01…05 |
| 2 | LVMDP | LOVATO DMG510 (Outcoming) | 3 | outcoming | RS485 | PM-LVMDP-OUT-01…03 |
| 3 | MVMDP | CEWE Elite440 (Digital Meter) | 1 | incoming | RS485 | PM-MVMDP-01 |
| 4 | MCC 1 | ACREL AMC96 | 2 | distribution | RS485 | PM-MCC1-01…02 |
| 5 | MCC 2 | ACREL AMC96 | 1 | distribution | RS485 | PM-MCC2-01 |
| 6 | MCC 3 | ACREL AMC96 | 2 | distribution | RS485 | PM-MCC3-01…02 |
| 7 | MCC 4 | ACREL AMC96 | 1 | distribution | RS485 | PM-MCC4-01 |
| 8 | MCC Pellet 1 | WEIDMULLER EM220 | 1 | distribution | RS485 | PM-PEL1-01 |
| 9 | MCC Pellet 2 | WEIDMULLER EM220 | 1 | distribution | RS485 | PM-PEL2-01 |
| 10 | MCC Pellet 3 | WEIDMULLER EM220 | 1 | distribution | RS485 | PM-PEL3-01 |
| | | **Total** | **18** | | | |

**Peran meter** (menentukan agregasi, lihat §7):

- `incoming` — sumber utama, energinya **tidak** dihitung ulang di panel anak
- `outcoming` — pengukuran keluar dari panel utama; **subset** dari `incoming`
- `distribution` — panel distribusi (MCC); anak dari `incoming`

---

## 3. Klasifikasi parameter: 3 lapis

Parameter tidak dikumpulkan semua lewat Modbus. Ada tiga lapis dengan alasan berbeda.

### 3.1 Lapis INTI — polled langsung dari meter

| Parameter | Satuan | Register native? | Keterangan |
|---|---|---|---|
| Voltage (L1/L2/L3) | V | ✅ semua model | Total = fasa pertama (3P4W) |
| Current (L1/L2/L3) | A | ✅ semua model | Perlu multiplier CT |
| Active power (kW) | kW | ✅ semua model | Daya kerja nyata |
| Apparent power (kVA) | kVA | ✅ semua model | Basis penopfanan & PF |
| Reactive power (kVAR) | kVAR | ✅ semua model | Indikator PF buruk |
| Active energy (kWh) | kWh | ✅ semua model | Register kumulatif |
| Reactive energy (kVARh) | kVARh | ✅ semua model | Dasar penalti PF |
| Frequency | Hz | ✅ semua model | Kualitas daya |

> **7 parameter inti × 18 meter.** Ini yang benar-benar dibaca lewat Modbus.

### 3.2 Lapis TURUNAN — dihitung di backend, TIDAK dipoll

| Parameter | Rumus | Alasan diturunkan |
|---|---|---|
| **Power Factor** | `PF = kW / kVA` | Register PF tiap model bisa berbeda definisi (PF total vs PF per fasa, tanda leading/trailing). Mengambil dari register ✗ bisa tidak konsisten dengan kW & kVA yang ditampilkan. |
| **kVAh (energy semu)** | `kVAh = kWh / PF` | **Hanya 1 dari 5 model (PAC3220) punya register kVAh.** 17 meter lain akan selalu 0. Untuk PF konstan, `∫kVA dt = ∫kW dt / PF`. |

> **Nilai turunan = sumber kebenaran tunggal.** Register PF dan kVAh dari meter
> diabaikan agar tidak ada dua angka berbeda untuk hal yang sama.

### 3.3 Lapis OPSIONAL — nullable, per meter

| Parameter | Satuan | Tersedia di | Syarat |
|---|---|---|---|
| **THD-I** (THD arus) | % | PAC3220, DMG510, Elite440, AMC96\* | AMC96 hanya bila opsi `/H` terpasang |
| **THD-U** (THD tegangan) | % | PAC3220, DMG510, Elite440, AMC96\* | idem |
| THD-P (THD daya) | % | Elite440 | rata-rata, s/d orde 31 |
| Unbalance Voltage | % | PAC3220 | |
| Unbalance Current | % | PAC3220 | |

\* **6 unit AMC96 wajib dicek fisik saat commissioning** — port `/H` di belakang unit.

Ketiga parameter ini **nullable** di seluruh stack. Meter yang tidak mendukungnya
harus menampilkan "tidak tersedia", **bukan** angka 0 — 0 berarti "sehat",
sedangkan "tidak tersedia" berarti "tidak bisa diukur".

### 3.4 Parameter yang TIDAK diambil

| Parameter | Alasan |
|---|---|
| THD per harmonik (orde 2..31) | Terlalu banyak register; THD total sudah cukup untuk screening. Tersedia bila butuh, via profil model. |
| Arus per fasa pada level detail | Sudah ada di lapis inti |
| Demand (max demand) | Tersedia di 4 model, format berbeda. Defer ke fase berikutnya. |
| Import/export energy terpisah | Hanya DMG510 & EM220 (4 kuadran). Defer ke fase berikutnya. |

---

## 4. Matriks kapabilitas

| | PAC3220 | DMG510 | Elite440 | AMC96 | EM220 |
|---|:--:|:--:|:--:|:--:|:--:|
| V / I / kW / kVA / kVAR | ✅ | ✅ | ✅ | ✅ | ✅ |
| kWh / kVARh | ✅ | ✅ | ✅ | ✅ | ✅ |
| **kVAh native** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **THD-I** | ✅ | ✅ | ✅ | ⚠️ `/H` | ❌ |
| THD-U | ✅ | ✅ | ✅ | ⚠️ `/H` | ❌ |
| Unbalance V / I | ✅ | ❌ | ❌ | ❌ | ❌ |
| PF | ✅ | ✅ | ✅ | ✅ | ✅ |
| Hz | ✅ | ✅ | ✅ | ✅ | ✅ |
| Demand | ✅ | ✅ | ✅ | ❌ | ✅ |
| Per fasa | ✅ | ✅ | ✅ | ✅ | ✅ |
| Orde harmonik maks | 40 | 15 | 31 | 31 | — |
| Akurasi daya | — | Class 1 (kWh) | 0,2s/0,5s/1,0 | Class 1,0 | 0,5S (kWh) |
| Data format | IEEE754 | int berskala | IEEE754 | int berskala | int berskala |
| Default bus | 19200,8N1 | 9600,8N1 | 9600,8N1 | 9600,8N1 | 9600,8N1 |
| Update internal | — | — | — | — | 1 detik |

**Ringkasan cakupan THD:** 5 (PAC3220) + 3 (DMG510) + 1 (Elite440) + 1 (AMC96 dgn `/H`)
= **10 dari 18 meter**. 3 unit EM220 sama sekali tidak mendukungnya.

---

## 5. Normalisasi di Node-RED

Node-RED **wajib** mengubah register mentah menjadi satuan engineering sebelum
publish ke MQTT. Nilai mentah tidak boleh keluar dari Node-RED.

### 5.1 Konversi wajib

```
engineering_value = raw_register / scale
```

Contoh: PAC3220 register 850 (float32) berisi 118.6 → publish `power: 118.6` kW.
Contoh: AMC96 register 6 (uint16) berisi 1186 → publish `power: 118.6` kW (skala 10).

### 5.2 Jebakan yang harus ditangani

| Jebakan | Detail | Penanganan |
|---|---|---|
| **Skala berbeda per model** | PAC3220 & Elite440: float skala 1. AMC96: uint16 skala 10. DMG510: int32 skala 100. EM220: uint32 skala 1000. | Ambil `scale` dari `meter-profiles.js` per model. **Jangan hardcode.** |
| **Float vs integer** | PAC3220 & Elite440 IEEE754 little-endian (2 register). | Decoder terpisah; `parseInt` akan menghasilkan 0 atau angka sampah. |
| **Register 32-bit terbelah** | kWh & kVARh = 2 register 16-bit, little-endian (low word dulu). | Gabung: `low + high × 65536`. |
| **Multiplier CT** | Meter menerima CT sekunder 1 A / 5 A. | Set rasio CT di alat. Verifikasi saat commissioning. |
| **KVAh** | 17 dari 18 meter tidak punya register ini. | **Jangan poll.** Hitung di backend dari kWh & PF. |
| **PF** | Definisi register berbeda antar model. | **Jangan poll.** Hitung di backend dari kW & kVA. |
| **THD tanpa `/H`** | AMC96 tanpa opsi `/H`: register tidak ada / nilai 0. | Publish `null`, bukan 0. |
| **DMG510 THD mati** | Perlu `P02.12 = THD+HAR`. | Set parameter saat commissioning, lalu verifikasi nilainya non-null. |

### 5.3 Kontrak payload MQTT

Topic: `ems/meter/{device_code}/telemetry`

```json
{
  "device_code": "PM-LVMDP-IN-03",
  "timestamp": "2026-10-21T08:30:00Z",

  "voltage": 402.8,
  "current": 80.4,
  "power": 52.8,
  "apparent_power": 60.0,
  "reactive_power": 28.2,
  "energy_active": 633.6,
  "energy_reactive": 287.4,
  "frequency": 50.03,

  "thd_current": 6.2,
  "thd_voltage": 2.4,
  "unbalance_voltage": 1.8,
  "unbalance_current": 5.1,

  "phases": {
    "L1": { "voltage": 403.1, "current": 26.8, "power": 17.6, "thd_current": 6.4 },
    "L2": { "voltage": 402.6, "current": 26.9, "power": 17.7, "thd_current": 6.1 },
    "L3": { "voltage": 402.7, "current": 26.7, "power": 17.5, "thd_current": 6.0 }
  }
}
```

Kaidah:

- Semua nilai sudah **satuan engineering** (SI), bukan register mentah.
- Field opsional yang tidak tersedia diisi **`null`**, bukan `0` dan bukan dihilangkan.
- `power_factor` **tidak** dikirim dari Node-RED — dihitung backend.
- `energy_apparent` (kVAh) **tidak** dikirim dari Node-RED — dihitung backend.
- Timestamp dalam ISO-8601 UTC.

---

## 6. Skema data backend

### 6.1 Tabel `devices`

| Kolom | Tipe | Keterangan |
|---|---|---|
| id | SERIAL PK | |
| device_code | TEXT UNIQUE | PM-LVMDP-IN-01 |
| name | TEXT | LVMDP Incoming 1 |
| location | TEXT | LVMDP |
| brand | TEXT | SIEMENS PAC3220 |
| model | TEXT | enum 5 model |
| role | TEXT | incoming / outcoming / distribution |
| modbus_address | INT | slave id |
| modbus_host | TEXT | IP converter / meter |
| transport | TEXT | rs485 / ethernet |
| capabilities | JSONB | kapabilitas efektif unit ini |
| is_active | BOOLEAN | |

> `capabilities` disimpan per **unit**, bukan per model, karena AMC96 ada yang
> punya opsi `/H` dan ada yang tidak.

### 6.2 Tabel `readings` (hypertable, TimescaleDB)

| Kolom | Tipe | Lapis | Satuan |
|---|---|---|---|
| time | TIMESTAMPTZ PK | | |
| device_id | INT FK | | |
| voltage | DOUBLE | inti | V |
| current | DOUBLE | inti | A |
| power | DOUBLE | inti | kW |
| apparent_power | DOUBLE | inti | kVA |
| reactive_power | DOUBLE | inti | kVAR |
| energy_active | DOUBLE | inti | kWh (kumulatif) |
| energy_reactive | DOUBLE | inti | kVARh (kumulatif) |
| frequency | DOUBLE | inti | Hz |
| power_factor | DOUBLE | **turunan** | 0..1 |
| energy_apparent | DOUBLE | **turunan** | kVAh (kumulatif) |
| thd_current | DOUBLE NULL | opsional | % |
| thd_voltage | DOUBLE NULL | opsional | % |
| unbalance_voltage | DOUBLE NULL | opsional | % |
| unbalance_current | DOUBLE NULL | opsional | % |

Partition 1 hari per chunk. Index `(device_id, time DESC)`.

### 6.3 Tabel `phase_readings` (hypertable terpisah)

| Kolom | Tipe | Satuan |
|---|---|---|
| time | TIMESTAMPTZ PK | |
| device_id | INT FK | |
| phase | TEXT | L1 / L2 / L3 |
| voltage | DOUBLE | V |
| current | DOUBLE | A |
| power | DOUBLE | kW |
| apparent_power | DOUBLE | kVA |
| reactive_power | DOUBLE | kVAR |
| power_factor | DOUBLE | 0..1 |
| thd_current | DOUBLE NULL | % |
| thd_voltage | DOUBLE NULL | % |

> Dipisah dari `readings` karena hanya sebagian meter yang mengukur per fasa,
> dan volumenya 3× lebih besar. Query per-fasa lebih sering dipakai saat
> troubleshooting MCC.

### 6.4 Tabel `alarms`

| Kolom | Tipe |
|---|---|
| id | SERIAL PK |
| device_id | INT FK |
| severity | TEXT (critical / warning / info) |
| message | TEXT |
| acknowledged | BOOLEAN |
| triggered_at | TIMESTAMPTZ |

---

## 7. Aturan agregasi

### 7.1 Menghindari double counting

Energi yang melewati 2 meter (mis. LVMDP Incoming → LVMDP Outcoming → MCC)
**dihitung berkali-kali** kalau semua dijumlahkan.

Aturan: **total sistem hanya menghitung meter ber-role `incoming`**
(LVMDP Incoming 5 + MVMDP 1 = 6 meter).

```
total_power = Σ power        untuk role = 'incoming'
total_energy= Σ energy_active untuk role = 'incoming'
```

Untuk per-panel: hitung `incoming` saja; `outcoming` dan `distribution` ditampilkan
sebagai rincian, bukan dijumlahkan ke total.

> Aturan ini harus berpindah ke backend. Frontend sekarang menerapkan aturan
> yang sama pada data mock.

### 7.2 Parameter turunan

```sql
-- Power factor
UPDATE readings SET power_factor = power / NULLIF(apparent_power, 0);

-- kVAh kumulatif (energy semu)
--_backfill_ saat insert, dari kWh & PF:
energy_apparent = energy_active / NULLIF(power / apparent_power, 0)
```

### 7.3 Energy: delta, bukan absolut

Register energy bersifat **kumulatif**. Untuk energi interval:

```
energy_interval = energy_sekarang - energy_sebelumnya
```

Guard: bila `energy_sekarang < energy_sebelumnya` → terjadi **overflow 32-bit**
atau reset meter. Tandai interval tersebut invalid, jangan simpan sebagai negatif.

---

## 8. Strategi sampling & penyimpanan

| Tingkat | Interval | Parameter | Retensi | Dipakai untuk |
|---|---|---|---|---|
| **Raw** | 5 detik | kW, kVA, kVAR, V, I | 7 hari | tampilan real-time, deteksi anomali |
| **Intraday** | 1 menit | 7 inti + 3 opsional | 90 hari | grafik shift, laporan harian |
| **Aggregate** | 15 menit | 7 inti | 2 tahun | grafik mingguan/bulanan, tren |
| **Rollup** | harian | kWh, kVARh, kVAh, min/max | ∞ | laporan, basis penalti PF |

Volume dengan 18 meter:

- 5 detik → 18 × 9 × 17 280 ≈ **2,8 juta baris/hari**
- 1 menit → 18 × 10 × 1 440 ≈ **259 ribu baris/hari** (≈ 95 juta/tahun)

Keduanya wajar untuk TimescaleDB. Yang **tidak** advisable: menyimpan semua
parameter per-detik selamanya, atau polling register energy tiap 1 detik.

> Catatan: EM220 memperbarui register internalnya tiap 1 detik, jadi polling
> 1 detik tidak menambah informasi — polling 5 detik cukup.

---

## 9. Pemetaan ke tampilan web

| Layar | Parameter | Sumber |
|---|---|---|
| **Overview** | Total Daya (kW), Daya Semu (kVA), Energy Hari Ini (kWh), Device Online | turunan + inti |
| **Real-time** | Per meter: kW, kVA, kVAR, PF, V, I, Hz, + chip THD-I di header | inti + turunan + opsional |
| **Real-time** | Per panel: kW, kVA, kVAR, kWh | agregasi panel |
| **History** | Chart kW + kVA + kVAR; ringkasan peak & PF | timeseries |
| **History** | Energy: kWh, kVARh, kVAh | timeseries (kVAh turunan) |
| **Power Quality** | THD-I, THD-U, unbalance, deviasi frekuensi, detail per fasa | opsional + `phase_readings` |
| **Devices** | **Hanya identitas**: device, merk, status, last seen | — |
| **Alarms** | Ambang PF, THD, tegangan, frekuensi, offline | `alarms` |

> Menu **Devices** sengaja tidak menampilkan nilai pengukuran — seluruhnya sudah
> tersedia di menu **Real-time**. Fungsi Devices = inventaris + status koneksi.

### 9.1 Aturan tampilan parameter opsional

- THD-I **tidak** ditampilkan sebagai kotak kosong pada meter yang tidak mendukungnya.
  Di kartu real-time: tampilkan "-" dengan label "THD-I".
- Di halaman **Power Quality**, meter tanpa THD dikumpulkan di daftar terpisah
  ("Meter Tanpa Data THD") beserta alasannya:
  - `Opsi /H belum terpasang` (AMC96)
  - `Model tanpa dukungan harmonik` (EM220)
- Ambang status THD (acuan IEC 61000-4-30):

| THD-I | Status |
|---|---|
| < 3% | baik |
| 3–5% | perlu perhatian |
| 5–8% | tidak sesuai standar |
| ≥ 8% | kritis |

---

## 10. Aturan alarm

| Parameter | Warning | Critical | Sumber |
|---|---|---|---|
| Power factor | < 0,90 | < 0,85 | turunan |
| Tegangan | di luar 385–415 V | di luar 350–440 V | inti |
| **Frekuensi** | deviasi > 0,5 Hz dari 50 Hz | deviasi > 1,0 Hz | inti |
| THD-I | ≥ 5% | ≥ 8% | opsional |
| Unbalance tegangan | > 2% | > 5% | opsional |
| Offline | heartbeat > 30 detik | > 3 menit | status |
| Beban | > 80% kapasitas | > 95% kapasitas | inti |

> Ambang THD/unbalance hanya berlaku pada meter yang mendukungnya.
> Ambang frekuensi mengacu IEC 61000-4-30 untuk grid 50 Hz.

### 10.1 Frekuensi sebagai parameter kualitas daya

Frekuensi diukur **semua** meter (tidak ada yang ограничен seperti THD), tapi
tetap ditampilkan terpisah karena merupakan indikator kualitas daya, bukan
konsumsi energi.

- Di halaman **Real-time**, frekuensi muncul sebagai metrik biasa di baris ketiga
  kartu meter (Tegangan / Arus / Frekuensi).
- Di halaman **Power Quality**, ada kartu "Deviasi Frekuensi" yang memisahkan
  meter yang keluar toleransi ±0,5 Hz dari nominal 50 Hz.
- Bandingkan antar meter: deviasi yang **seragam** di semua meter menandakan
  masalah di sisi grid (PLN/genset), sedangkan deviasi yang hanya di satu meter
  menandakan masalah lokal (mis. harmonik dari motor pelletizer).

---

## 11. Checklist commissioning

**Per meter**

- [ ] Slave ID diubah dari default 1 menjadi unik
- [ ] Baud / parity / stop bit sesuai model
- [ ] Rasio CT terpasang benar (mis. 100/5 = 20)
- [ ] Register kW dicek terhadap display panel / clamp meter
- [ ] Register kWh dicek terhadap pembaca Counter watt-hour
- [ ] PF dihitung manual dari kW & kVA, dibandingkan dengan register PF
- [ ] Type & endianness register (float vs int, 1 vs 2 register)

**Khusus per model**

- [ ] **AMC96** — cek fisik keberadaan opsi `/H` pada 6 unit (untuk THD)
- [ ] **DMG510** — set `P02.12 = THD+HAR` pada 3 unit (untuk THD)
- [ ] **PAC3220** — pastikan jalur Ethernet, bukan lewat converter RS485
- [ ] **Elite440** — konfirmasi pemetaan baris multi-line (L1/L2/L3)
- [ ] **EM220** — pastikan mode 3P4W / rasio CT benar

**Jaringan**

- [ ] Panjang tiap segmen RS485 < 1.200 m
- [ ] Terminating resistor 120 Ω di ujung bus
- [ ] Uji komunikasi saat beban puncak (noise dari motor pelletizer)
- [ ] Beban polling dihitung: register/meter ÷ (jumlah register × baud)

---

## 12. Pertanyaan terbuka untuk tim elektrikal

1. **Topologi MCC** — apakah MCC 1–4 dan MCC Pellet 1–3 disuplai dari LVMDP
   atau MVMDP? Ini menentukan apakah aturan agregasi §7.1 sudah benar.
2. **Meter LVMDP Incoming 5 unit** — apakah semuanya meter incoming utama,
   atau sebagian hanya monitoring sub-feeder? Jika sebagian hanya sub-feeder,
   aturan total sistem harus disesuaikan.
3. **Opsi `/H` pada AMC96** — unit mana yang sudah terpasang?
4. **Tarif & penalti PF** — hapus fitur estimasi biaya dari UI, tetapi apakah
   data PF & kVARh tetap dibutuhkan untuk pengajuan penalti ke PLN?
5. **Meter 7SR51** — ada datasheet Siemens 7SR51 di folder yang tidak masuk
   rekap 18 meter. Apakah itu relay proteksi (bukan power meter)?
6. **Nilai CT** — daftar rasio CT per instalasi untuk verifikasi multiplier.

---

## 13. Lampiran — sumber datasheet

| Model | Dokumen | Lokasi |
|---|---|---|
| SIEMENS PAC3220 | Equipment Manual, L1V30425208F_RS-AA_002, 07/2024 (160 hal) | `Datasheet Power Meter/Siemens PAC3220 Datasheet.pdf` |
| LOVATO DMG510 | Installation manual, 604 GB I 09 19 (12 hal) | `Datasheet Power Meter/Lovato DMG510 Datasheet.pdf` |
| CEWE Elite440 | Datasheet, 7-18/Nov 21 (4 hal) | `Datasheet Power Meter/Elite440 CEWE Datasheet.pdf` |
| ACREL AMC96 | Datasheet AMC96L-E4 (2 hal) | `Datasheet Power Meter/Acrel AMC96 Datasheet.pdf` |
| WEIDMULLER EM220 | Data sheet EM220-RTU-4DI2DO, 25.02.2026 (4 hal) | `Datasheet Power Meter/Weidmuller EM220 Datasheet.pdf` |
| SIEMENS 7SR51 | — (tidak dipakai sebagai power meter) | `Datasheet Power Meter/Siemens 7SR51 Datasheet.pdf` |
