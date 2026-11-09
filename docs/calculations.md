# Inventaris Perhitungan EMS

Dokumen ini mencatat rumus dan agregasi numerik yang diterapkan di project,
termasuk kalkulasi telemetry, query, alarm, UI, serta generator data demo.
Nilai yang langsung dibaca dari register meter bukan hasil rumus EMS, tetapi
konversi register ke nilai engineering tetap dicatat di sini.

## Aturan pemeliharaan

**Setiap penambahan atau perubahan perhitungan harus memperbarui dokumen ini
dalam perubahan kode yang sama.** Catat rumus yang benar-benar dijalankan,
kondisi input/batasnya, lokasi implementasi, dan apakah perhitungan berlaku
untuk telemetry produksi, agregasi/UI, atau data demo. Jangan menyalin rumus
dari dokumen desain tanpa mencocokkannya dengan implementasi.

Instruksi ini juga berlaku untuk perubahan rumus dalam Python, TypeScript,
SQL, query database, simulator, dan fixture frontend. Lihat
`.github/instructions/calculations.instructions.md` untuk pengingat otomatis
saat mengubah file kode yang relevan.

## Notasi dan ruang lingkup

- `P` = daya aktif (kW), `S` = daya semu (kVA), `Q` = daya reaktif (kVAR).
- `E` = energi aktif (kWh), `PF` = power factor, `V` = tegangan (V),
  `I` = arus (A), dan `f` = frekuensi (Hz).
- Rumus simulator/fixture menghasilkan data sintetis; rumus tersebut bukan
  pengganti nilai aktual dari power meter.
- Format tanggal, pembulatan untuk tampilan umum, fungsi acak, dan operasi
  aritmetika yang hanya mengatur layout tidak dicantumkan kecuali berpengaruh
  pada metrik, status, atau rentang analisis EMS.

## 1. Dekode dan normalisasi telemetry

| Perhitungan | Rumus / aturan implementasi | Lokasi dan penggunaan |
|---|---|---|
| Skala register ke engineering value | `nilai = raw / skala_register`, dibulatkan 3 desimal. Skala ditetapkan per register/model. | [`backend/app/acquisition/decoder.py`](../backend/app/acquisition/decoder.py); profil dan skalanya di [`backend/app/acquisition/profiles.py`](../backend/app/acquisition/profiles.py). |
| Interpretasi integer signed | `int16 = raw - 2^16` jika `raw > 2^15 - 1`; `int32 = raw - 2^32` jika nilai unsigned `> 2^31 - 1`; selain itu nilai dipertahankan. | [`backend/app/acquisition/decoder.py`](../backend/app/acquisition/decoder.py). |
| Gabung register 32-bit | Little-endian: `low + high × 65536`. Big-endian: `high × 65536 + low`. | [`backend/app/acquisition/decoder.py`](../backend/app/acquisition/decoder.py). |
| Nilai tegangan/arus meter rata-rata | `mean(x) = Σ nilai fasa yang tersedia / jumlah nilai fasa yang tersedia`; hasil dibulatkan 3 desimal. Jika tidak ada input, hasil `null`. | [`backend/app/acquisition/normalize.py`](../backend/app/acquisition/normalize.py). Arus mengambil arus fasa. |
| Tegangan L-N dan L-L | `voltage_ln = mean(V L1, V L2, V L3)` (fasa-netral, ~230 V); `voltage_ll = mean(V L1-L2, V L2-L3, V L3-L1)` (antar-fasa, ~400 V). Masing-masing `null` bila register tidak dimiliki model meter (PAC3220 hanya L-L; DMG510, Elite440, AMC96, EM220 hanya L-N). | [`backend/app/acquisition/normalize.py`](../backend/app/acquisition/normalize.py). Dikirim di payload MQTT untuk evaluasi alarm; tidak disimpan sebagai kolom terpisah. |
| Tegangan sistem `voltage` (disimpan) | Selalu bermakna L-L. `voltage = voltage_ll` bila terukur; jika tidak, `voltage = voltage_ln × √3` (pendekatan sistem tiga fasa seimbang), dibulatkan 3 desimal. | [`backend/app/acquisition/normalize.py`](../backend/app/acquisition/normalize.py); disimpan di `readings.voltage`. |
| Tegangan per fasa | Memakai L-N per fasa bila tersedia; jika model hanya punya L-L, memakai pasangan antar-fasa (L1-L2, L2-L3, L3-L1). | [`backend/app/acquisition/normalize.py`](../backend/app/acquisition/normalize.py); disimpan di `phase_readings.voltage`. |
| THD-I dan THD-U total | Rata-rata nilai THD per fasa yang tersedia, dengan aturan mean yang sama. Hasil dijadikan `null` bila kapabilitas meter menyatakan parameter tidak didukung. | [`backend/app/acquisition/normalize.py`](../backend/app/acquisition/normalize.py). |
| Nilai per fasa | Tegangan, arus, daya, kVA, kVAR dan THD per fasa diteruskan ke payload sesuai nilai register; pada jalur telemetry nyata tidak dibentuk ulang di normalizer. | [`backend/app/acquisition/normalize.py`](../backend/app/acquisition/normalize.py). PF per fasa kemudian dihitung backend seperti pada §2. |

## 2. Perhitungan telemetry backend

| Perhitungan | Rumus / aturan implementasi | Lokasi dan penggunaan |
|---|---|---|
| PF total dan per fasa | `PF = abs(P / S)`, dibulatkan 3 desimal. Jika P atau S kosong, atau S = 0, hasil `null`. PF yang dikirim meter ditimpa. | [`backend/app/services/derive.py`](../backend/app/services/derive.py), dipanggil saat ingest di [`backend/app/services/ingest.py`](../backend/app/services/ingest.py). |
| Energi semu | `kVAh = kWh / PF`, dibulatkan 2 desimal. Jika kWh kosong atau PF kosong/nol, hasil `null`. | [`backend/app/services/derive.py`](../backend/app/services/derive.py); nilai disimpan bersama telemetry di [`backend/app/services/ingest.py`](../backend/app/services/ingest.py). |

**Catatan semantik kVAh:** implementasi membagi energi kWh kumulatif dengan PF pada
sampel saat itu. Ini pendekatan yang tercantum dalam spesifikasi project, bukan
integrasi historis `Σ(kVA × durasi)`. Jika PF berubah terhadap waktu, keduanya
dapat berbeda.

## 3. Agregasi query, ringkasan, dan histori

### Backend

| Perhitungan | Rumus / aturan implementasi | Lokasi dan penggunaan |
|---|---|---|
| Awal "hari ini" | 00:00 zona waktu lokal (`Settings.timezone`, default `Asia/Jakarta`/WIB), dikonversi ke UTC (= 17:00 UTC hari sebelumnya). | `local_day_start` di [`backend/app/services/queries.py`](../backend/app/services/queries.py). |
| Total energi rentang waktu | Per meter: `delta = last(E) - first(E)` dalam rentang; total = `Σ delta` untuk delta yang tersedia dan `> 0` (delta negatif akibat counter reset/meter diganti diabaikan). Berlaku untuk kWh, kVARh, dan kVAh. Sumber: `readings_1min` (nilai counter terakhir tiap menit), sehingga `first` = counter di akhir menit pertama rentang (presisi ±1 menit) dan tetap tersedia setelah data mentah dihapus retensi. | `get_energy_totals` di [`backend/app/services/queries.py`](../backend/app/services/queries.py); endpoint `GET /api/energy` di [`backend/app/api/readings.py`](../backend/app/api/readings.py); dipakai halaman History. |
| Energi aktif hari ini | Total energi aktif meter incoming (rumus baris di atas) dari awal hari lokal sampai sekarang. | `get_summary` di [`backend/app/services/queries.py`](../backend/app/services/queries.py). |
| Ringkasan daya sistem | Menjumlahkan P, S, dan Q dari meter ber-role `incoming`. Query tidak menerapkan filter status offline pada daftar incoming; nilai terakhir yang tersimpan tetap dapat ikut terhitung. | `get_summary` di [`backend/app/services/queries.py`](../backend/app/services/queries.py). |
| Jumlah meter per status | Menghitung banyak perangkat berstatus `online`, `warning`, dan `offline`; total perangkat = jumlah seluruh perangkat. | `get_summary` di [`backend/app/services/queries.py`](../backend/app/services/queries.py) dan fallback demo di [`frontend/src/lib/mock-data.ts`](../frontend/src/lib/mock-data.ts). |
| Time series tanpa bucket, satu meter | Mengembalikan pembacaan tersimpan tanpa menghitung ulang nilai per-meter. | Cabang raw per-device di [`backend/app/services/queries.py`](../backend/app/services/queries.py). |
| Time series tanpa bucket, beberapa meter | Tidak dikelompokkan per timestamp persis (tiap meter dibaca pada detik berbeda). Diproses sebagai bucket `1 minute` (`AGGREGATE_RAW_INTERVAL`) dengan rumus bucket di bawah. |
| Sumber data time series ber-bucket | Semua bucket `1m`–`1d` (dan raw gabungan) dibaca dari continuous aggregate `readings_1min` lalu di-`time_bucket` ulang. Nilai rata-rata = rata-rata dari rata-rata per menit (setara karena jumlah sampel per menit sama); energi = `last` per bucket. `readings_1min` memakai `materialized_only = false` sehingga menit terbaru ikut dihitung real-time. |
| Batas rentang query | Raw maksimal 7 hari. Bucket lain: `rentang / durasi_bucket <= 20.000` titik (1m ≈ 13,9 hari, 5m ≈ 69 hari, 15m ≈ 208 hari, 1h ≈ 2,3 tahun). Pelanggaran → HTTP 400. | `get_readings` di [`backend/app/services/queries.py`](../backend/app/services/queries.py). |
| Batas bucket harian | Bucket `1d` memakai `time_bucket('1 day', time, 'Asia/Jakarta')` sehingga satu hari = 00:00–24:00 WIB. Bucket lain memakai `time_bucket` biasa. Label titik (`HH:MM`) ditampilkan dalam waktu lokal. | `_bucket_expr` dan `_point` di [`backend/app/services/queries.py`](../backend/app/services/queries.py). |
| Rata-rata dalam bucket per meter | P, S, Q, V, I, f, dan THD-I memakai `AVG` (atas nilai per menit `readings_1min`); energi memakai nilai terakhir (`last`) pada bucket; PF per meter di bucket = `AVG(P) / AVG(S)` (PF dari agregat tidak dipakai). | Subquery bucket per meter di [`backend/app/services/queries.py`](../backend/app/services/queries.py). |
| Gabungan meter di bucket | P, S, Q, dan energi per-meter dijumlahkan; V, I, f, dan THD-I antar-meter dirata-ratakan; PF gabungan = `Σ AVG(P per meter) / Σ AVG(S per meter)`. | Query akhir bucket di [`backend/app/services/queries.py`](../backend/app/services/queries.py). |
| Continuous aggregate 1 menit dan 15 menit | Daya, V, I, f, dan PF menggunakan `AVG`; THD-I/THD-U juga menggunakan `AVG` di bucket 1 menit. Register energi menggunakan nilai `last` dalam bucket. | View `readings_1min` dan `readings_15min` di [`database/init/01-schema.sql`](../database/init/01-schema.sql). |
| Rollup energi harian | Hari = `time_bucket('1 day', time, 'Asia/Jakarta')` (00:00 WIB). `energy_kwh = last(kWh) - first(kWh)`; `energy_kvarh = last(kVARh) - first(kVARh)`; daya puncak = `MAX(P)`; PF rata-rata = `AVG(PF)`. | View `daily_energy` di [`database/init/01-schema.sql`](../database/init/01-schema.sql); migrasi DB berjalan di [`database/migrations/001-daily-energy-wib.sql`](../database/migrations/001-daily-energy-wib.sql). |
| Peringkat severity alarm perangkat | Critical dipetakan ke 2, warning ke 1, lainnya ke 0; perangkat memakai nilai maksimum severity alarm yang masih terbuka. | `_severity_rank` di [`backend/app/services/queries.py`](../backend/app/services/queries.py). |

### Frontend

| Perhitungan | Rumus / aturan implementasi | Lokasi dan penggunaan |
|---|---|---|
| Total daya realtime | Saat pesan WebSocket diterima, `totalPower`/`totalApparentPower`/`totalReactivePower` = jumlah P/S/Q meter role `incoming` dari data device terbaru (sama dengan rumus ringkasan backend). Energi hari ini dan jumlah status tetap dari `GET /api/summary/today` (sinkron tiap 60 detik). Tidak berlaku di mode demo. | `withLiveTotals` di [`frontend/src/lib/realtime.ts`](../frontend/src/lib/realtime.ts), dipakai [`frontend/src/lib/use-ems-data.ts`](../frontend/src/lib/use-ems-data.ts). |
| Total panel | Untuk meter dalam panel, kecualikan role `outcoming` dan meter offline; jumlahkan P, S, Q, dan kWh. | [`frontend/src/lib/device-data.ts`](../frontend/src/lib/device-data.ts); fixture panel juga dihitung di [`frontend/src/lib/mock-data.ts`](../frontend/src/lib/mock-data.ts). |
| Persentase status perangkat | `round(jumlah status / total perangkat × 100)`; jika total 0, hasil 0%. | [`frontend/src/components/dashboard/device-status-summary.tsx`](../frontend/src/components/dashboard/device-status-summary.tsx). |
| Ringkasan histori | Energi kWh/kVARh/kVAh diambil dari `GET /api/energy` (jumlah delta per meter, lihat tabel backend). Hanya pada mode demo (`NEXT_PUBLIC_DEMO_MODE=true`) dipakai `max(0, energi titik terakhir - energi titik pertama)` dari fixture. Puncak daya = maksimum seri; rata-rata P = `ΣP / jumlah titik`. | [`frontend/src/app/history/page.tsx`](../frontend/src/app/history/page.tsx). |
| PF rata-rata histori | Rata-rata P dibagi rata-rata S. UI menampilkan `-` jika daya semu puncak tidak positif. | [`frontend/src/app/history/page.tsx`](../frontend/src/app/history/page.tsx). |
| Ringkasan Power Quality | Menentukan THD-I maksimum, THD-U maksimum per panel, serta frekuensi minimum/maksimum dan jumlah meter yang melewati ambang. | [`frontend/src/app/power-quality/page.tsx`](../frontend/src/app/power-quality/page.tsx). |
| Skala progress THD | `min(100, THD-I / ambang_kritis × 100)` sebagai lebar progress bar. | [`frontend/src/app/power-quality/page.tsx`](../frontend/src/app/power-quality/page.tsx). |

**Perbedaan agregasi sumber:** ringkasan backend menjumlahkan incoming tanpa
memfilter status offline, sedangkan fallback demo `getTotals()` di
[`frontend/src/lib/mock-data.ts`](../frontend/src/lib/mock-data.ts)
mengeluarkan meter offline. Fallback demo juga menjumlahkan nilai energi fixture,
bukan menghitung delta dari histori telemetry.

## 4. Alarm dan status perangkat

### Ambang backend

Implementasi di [`backend/app/services/alarms.py`](../backend/app/services/alarms.py):

| Metrik | Rumus / kondisi warning | Kondisi critical |
|---|---|---|
| PF | `PF < 0.90` | `PF < 0.85` |
| Tegangan L-L (antar-fasa) | `0 < V < 385` atau `V > 415` | `0 < V < 350` atau `V > 440` |
| Tegangan L-N (fasa-netral) | `0 < V < 222.3` atau `V > 239.6` | `0 < V < 202.1` atau `V > 254.0` |
| Deviasi frekuensi | `abs(f - 50 Hz) > 0.5 Hz` | `abs(f - 50 Hz) > 1.0 Hz` |
| THD arus | `THD-I >= 5%` | `THD-I >= 8%` |
| Unbalance tegangan | `unbalance V > 2%` | `unbalance V > 5%` |
| Beban terhadap kapasitas | `P / rated_power_kW > 0.80` | `P / rated_power_kW > 0.95` |

Beban dihitung hanya bila kapasitas terpasang dan P bernilai truthy. Alarm
frekuensi dan tegangan juga memerlukan input lebih dari nol.

Batas L-N = batas L-L dibagi √3 (dibulatkan 1 desimal). Alarm tegangan memakai
tegangan yang benar-benar diukur meter: `voltage_ln` bila ada, lalu
`voltage_ll`, lalu `voltage` (dianggap L-L) untuk payload lama. Pesan alarm
menyebut jenis tegangannya (L-N atau L-L).

### Delay dan hysteresis alarm

Implementasi `apply_alarms` di
[`backend/app/services/alarms.py`](../backend/app/services/alarms.py), berlaku
untuk telemetry produksi maupun simulator (alarm `offline` dikelola terpisah):

- **Delay aktif:** alarm baru dibuat bila kondisi abnormal (ambang di atas)
  terdeteksi terus-menerus selama `waktu_sekarang - waktu_pertama_abnormal >=
  ALARM_ON_DELAY_SECONDS` (default 30 detik). Kondisi yang hilang sebelum itu
  diabaikan. Waktu yang dipakai adalah timestamp telemetry.
- **Deadband:** alarm yang sudah aktif dievaluasi dengan ambang yang digeser ke
  arah normal: PF `+0.01`; tegangan L-L `±4 V`, L-N `±2.3 V` (1% nominal);
  deviasi frekuensi `-0.1 Hz`; THD-I `-0.5` poin; unbalance V `-0.3` poin;
  beban `-0.03` (3% kapasitas). Contoh: alarm PF < 0.90 tetap aktif sampai
  PF ≥ 0.91.
- **Delay normal:** alarm aktif di-clear bila nilai berada di luar deadband
  selama `>= ALARM_OFF_DELAY_SECONDS` (default 30 detik).
- Severity alarm aktif mengikuti evaluasi ambang normal; di zona deadband
  memakai evaluasi ber-deadband.
- **Notifikasi Telegram:** alarm berseverity `critical` dikirim sekali
  (`EMS ALARM KRITIS`); notifikasi pulih (`EMS ALARM PULIH`) dikirim saat alarm
  di-clear atau turun ke `warning`.

### Status, threshold UI, dan timeout

- Deviasi frekuensi yang ditampilkan UI: `abs(f - 50 Hz)`. Status warning
  dimulai pada `>= 0.5 Hz`, critical pada `>= 1.0 Hz`; aturan UI berada di
  [`frontend/src/lib/meter-models.ts`](../frontend/src/lib/meter-models.ts).
  Ini sedikit berbeda dari kondisi backend yang memakai `>` bukan `>=`.
- Severity THD UI: critical jika `THD-I >= 8%`, warning jika `>= 5%`; lihat
  fungsi `thdSeverity` di [`frontend/src/lib/meter-models.ts`](../frontend/src/lib/meter-models.ts).
- Umur telemetry: `age_seconds = waktu_sekarang - last_seen_at`. Status koneksi
  dibandingkan dengan batas warning/offline konfigurasi; heartbeat dievaluasi
  dengan selisih waktu yang sama. Implementasi ada di
  [`backend/app/services/realtime.py`](../backend/app/services/realtime.py)
  dan [`backend/app/main.py`](../backend/app/main.py).
- Rate limit laporan client error: buang timestamp laporan jika
  `waktu_monotonic_sekarang - waktu_laporan > 60 detik`; tolak request jika
  masih ada 30 laporan dalam jendela tersebut. Implementasi di
  [`backend/app/api/client_errors.py`](../backend/app/api/client_errors.py).

## 5. Perhitungan khusus data demo dan simulasi

Rumus pada bagian ini membangkitkan data untuk demo/fixture atau seed database,
bukan nilai hitung telemetry aktual.

### Simulator backend

Di [`backend/app/acquisition/simulator.py`](../backend/app/acquisition/simulator.py):

- Load factor harian adalah fungsi bertingkat dari jam: `<6: 0.25`, `<8: 0.55`,
  `<11: 0.95`, `<14: 1.15`, `<17: 1.00`, `<20: 0.70`, selebihnya `0.35`.
- `jitter = 0.97 + random × 0.06`; `P = daya_nominal × load_factor × jitter`.
- `S = P / PF` (atau P bila PF nol).
- `Q = P × tan(acos(clamp(PF, 0.01, 0.999)))` untuk `0 < PF < 1`, selain itu 0.
- Tegangan antar-fasa simulasi `V_LL = 400 + (random - 0.5) × 4`; tegangan
  fasa-netral `V_LN = V_LL / √3` (~231 V) dengan offset per fasa `+0.2`, `-0.1`, `0`.
  Simulator hanya mengirim register tegangan yang dimiliki model meter
  (PAC3220: L-L saja; model lain: L-N saja), sesuai `PROFILES`.
- Arus perkiraan tiga fasa `I = S × 1000 / (sqrt(3) × V_LL)` (atau 0 jika V nol).
- Energi aktif simulasi `E = energi_awal + daya_nominal × 0.59 × elapsed_days`,
  dengan `elapsed_days` dihitung dari titik tetap `2026-01-01 00:00 UTC` agar
  counter selalu naik (monoton) seperti meter asli; energi reaktif simulasi
  `kVARh = E × 0.4`.
- Frekuensi `f = 50 + (random - 0.5) × 0.06`.
- Nilai arus per fasa disintesis sebagai `I × 0.34`, `I × 0.33`, `I × 0.33`;
  tegangan fasa ditambah offset kecil dari tegangan dasar.

### Fixture dan profil frontend

Di [`frontend/src/lib/mock-data.ts`](../frontend/src/lib/mock-data.ts):

- `S = P / PF`; `Q = P × tan(acos(PF))`.
- Pembagian fasa memakai bobot acak deterministik `w = 0.3 + random × 0.08`,
  dinormalisasi `share_i = w_i / Σw`; P, I, dan S tiap fasa dikalikan share.
  Tegangan fasa diberi variasi kecil; THD fasa diberi jitter.
- Profil per jam, hari, atau minggu memakai load profile, PF sintetis, lalu
  `S = P / PF` dan `Q = P × tan(acos(PF))`. Energi kumulatif ditambah dengan
  `daya × durasi`: satu jam untuk profil per jam, 24 jam untuk harian, dan
  `24 × 7` jam untuk mingguan.
- Arus profil ditaksir dengan `I = P × 1000 / (380 × 1.732 × 0.93)`.
- Total demo incoming mengecualikan meter offline dan menghitung jumlah nilai
  daya/energi; persentase statistik dan nilai tampilan dibulatkan sesuai fungsi
  yang dipanggil.
- Jumlah meter fixture = `Σ jumlah meter tiap grup`; jumlah status demo = banyak
  perangkat yang cocok dengan status tersebut. Untuk generator profil 24 jam,
  `P = max(8, loadShape(jam) × 400 × (0.92 + random × 0.16))`,
  `PF = 0.88 + random × 0.07`, `V = 398 + random × 5`,
  `f = 50 + (random - 0.5) × 0.06`, dan `THD-I = 2 + random × 4`.
  Load shape per jam: `<6: 0.15`, `<8: 0.35`, `<11: 0.70`, `<14: 0.95`,
  `<17: 0.85`, `<20: 0.50`, selebihnya `0.25`.
- Generator histori rentang tanggal menggunakan load per jam seperti di atas
  untuk rentang sampai 2 hari; rentang 3–60 hari memakai
  `P = 300 × (0.85 + random × 0.30)` per hari; di atas 60 hari memakai rumus
  daya yang sama per minggu. Energi simulasi diakumulasikan sebagai `P × durasi`
  (1, 24, atau 168 jam). Pada generator histori ini arus diisi 0, tegangan
  `398 + random × 5`, frekuensi `50 + (random - 0.5) × 0.06`, dan THD-I
  `2 + random × 4`.
- Pembulatan fixture: `round1(n) = round(n × 10) / 10`,
  `round2(n) = round(n × 100) / 100`; beberapa nilai generator simulator
  backend dibulatkan 3 desimal.
- Untuk fase fixture dengan seed tetap, seed awal berasal dari
  `seed = (Σ kode_karakter × 2654435761) mod 2^32`. Pada setiap iterasi:
  `a = (a + 0x6d2b79f5) mod 2^32`;
  `t = imul(a XOR (a >>> 15), 1 OR a)`;
  `t = (t + imul(t XOR (t >>> 7), 61 OR t)) XOR t`;
  hasil acak = `((t XOR (t >>> 14)) unsigned) / 2^32`.
  Seed histori rentang menggunakan
  `(Σ kode_karakter_tanggal_mulai × 31 + jumlah_hari) mod 2^32`.
  Ini menjaga data fixture konsisten; bukan rumus metrik listrik.

### Seed histori SQL

Di [`scripts/seed-history.sql`](../scripts/seed-history.sql) (dijalankan manual, tidak lagi otomatis),
data histori sintetis dibangkitkan tiap 15 menit:

- Tegangan `V = 400 + 2.5 × sin(epoch/3000 + device_id)`.
- Load factor = load berdasarkan jam × faktor hari (Sabtu `0.78`, Minggu `0.62`,
  hari lain `1.0`) × variasi `1 + 0.08 × sin(epoch/7200 + device_id)`.
- PF = `clamp(base_PF + 0.015 × sin(epoch/3600 + device_id), 0.85, 0.99)`.
- Energi aktif = `energi_awal + daya_nominal × 0.59 × elapsed_days`.
- `P = daya_nominal × load_factor`; `S = P/PF`; `Q = P × tan(acos(PF))`.
- `kVAh = kWh/PF`; `kVARh = kWh × tan(acos(PF))`.
- Arus `I = P × 1000 / (sqrt(3) × V × PF)`; frekuensi
  `f = 50 + 0.03 × sin(epoch/1800 + device_id)`.
- THD-I = `1.5 + 4 × (0.5 + 0.5 × sin(epoch/2400 + device_id))`;
  THD-U = `0.8 + 2 × (0.5 + 0.5 × sin(epoch/3600 + device_id))`;
  unbalance V = `0.3 + 1.5 × (0.5 + 0.5 × sin(epoch/4200 + device_id))`;
  unbalance I = `1 + 3 × (0.5 + 0.5 × sin(epoch/3000 + device_id))`.
  Nilai tersebut hanya dimasukkan jika capability meter mendukungnya.
- Daya/arus per fasa dikalikan konstanta `power_share`/`current_factor`;
  tegangan fasa = `V/sqrt(3) + voltage_offset`. THD per fasa memakai formula
  THD-I/THD-U yang sama, dengan `phase_offset` ditambahkan ke argumen sinus.

## 6. Perhitungan lain yang tidak membentuk parameter meter

- Rentang hari histori: `floor((tanggal_akhir - tanggal_awal) / 86,400,000) + 1`;
  digunakan untuk memilih bucket tampilan dan resolusi fixture di
  [`frontend/src/app/history/page.tsx`](../frontend/src/app/history/page.tsx)
  dan [`frontend/src/lib/mock-data.ts`](../frontend/src/lib/mock-data.ts).
- Default rentang endpoint readings: `to = waktu sekarang`, `from = to - 24 jam`
  jika pemanggil tidak menentukan waktu. Preset frontend membentuk tanggal
  relatif terhadap hari ini. Implementasi endpoint ada di
  [`backend/app/api/readings.py`](../backend/app/api/readings.py).
- Pemilihan bucket time series menggunakan interval tetap (`1m`, `5m`, `15m`,
  `1h`, `1d`) melalui `time_bucket`; ini pengelompokan waktu, bukan rumus
  kelistrikan. Implementasinya ada di
  [`backend/app/services/queries.py`](../backend/app/services/queries.py).

## Sumber acuan terkait

- [Spesifikasi parameter dan rumus Lapis Turunan](./parameter-specification.md)
- [Model data dan agregasi energi](./data-model.md)
- [Arsitektur akuisisi dan simulator](./architecture.md)
