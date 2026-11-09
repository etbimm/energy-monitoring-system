# Rancangan Fitur Deteksi Losses (Energy Balance)

Status: **rancangan — belum diimplementasi.**
Topologi pada dokumen ini masih **asumsi** dan wajib dicocokkan dengan single
line diagram (SLD) pabrik sebelum diimplementasi (lihat [§9](#9-pertanyaan-terbuka)).

---

## 1. Tujuan

Membandingkan energi yang **masuk** ke suatu titik distribusi dengan energi
yang **keluar** darinya, lalu:

1. Menampilkan neraca energi (kWh masuk, kWh keluar, selisih, % selisih) per
   jam dan per hari.
2. Memberi alarm jika selisih melewati ambang secara konsisten.
3. Memberi peringatan *mismatch* jika selisih negatif (keluar > masuk), yang
   hampir selalu berarti salah CT ratio, salah wiring, atau salah mapping.

Istilah di UI: **"Energi Tak Terukur"**, bukan "Losses" murni, karena selisih
juga mencakup beban tanpa meter (penerangan, kantor, dsb.) selain rugi kabel
atau trafo.

## 2. Konsep: node neraca

Neraca tidak dihitung per meter, melainkan per **node**: batas imajiner di
sekeliling satu bagian jaringan. Setiap node punya meter sisi **masuk** dan
meter sisi **keluar**.

```
loss_kwh = Σ ΔkWh(meter masuk) − Σ ΔkWh(meter keluar)
loss_pct = loss_kwh / Σ ΔkWh(meter masuk) × 100
```

Model many-to-many ini menangani kasus yang tidak bisa ditangani kolom
`parent_device_id` sederhana, misalnya 5 incoming yang memasok satu busbar.

### Jenis node

| `kind` | Arti | Losses wajar |
|---|---|---|
| `transformer` | MV → LV (rugi besi + tembaga trafo) | ± 1–3 % |
| `busbar` | Satu panel: incoming vs outgoing di panel yang sama | ≈ 0 % (selisih = beban tanpa meter + error meter) |
| `feeder` | Kabel dari outgoing satu panel ke incoming panel hilir | ± 1–3 % |

### Topologi asumsi (WAJIB dikonfirmasi ke SLD)

```
PM-MVMDP-01 ──[TRAFO]──► PM-LVMDP-IN-01..05 ──[BUSBAR LVMDP]──► PM-LVMDP-OUT-01..03
                                                                   │
                                     ┌─────────[FEEDER]────────────┘
                                     ▼
                        PM-MCC*-*, PM-PEL*-*   (pembagian per outgoing belum diketahui)
```

| Node (asumsi) | Masuk | Keluar |
|---|---|---|
| `TRF-MAIN` (transformer) | PM-MVMDP-01 | PM-LVMDP-IN-01..05 |
| `BUS-LVMDP` (busbar) | PM-LVMDP-IN-01..05 | PM-LVMDP-OUT-01..03 |
| `FDR-OUT-01` (feeder) | PM-LVMDP-OUT-01 | *(MCC/Pellet yang dipasok — TBD)* |
| `FDR-OUT-02` (feeder) | PM-LVMDP-OUT-02 | *(TBD)* |
| `FDR-OUT-03` (feeder) | PM-LVMDP-OUT-03 | *(TBD)* |

Node yang meter sisi keluarnya belum lengkap **tidak boleh diaktifkan**,
karena selisihnya akan terbaca besar dan menyesatkan.

## 3. Model data

Migrasi baru `database/migrations/004-energy-balance.sql` (ditambahkan juga
ke `database/init/01-schema.sql` agar instalasi baru langsung punya tabelnya).

```sql
CREATE TABLE IF NOT EXISTS balance_nodes (
  id                 SERIAL PRIMARY KEY,
  code               TEXT UNIQUE NOT NULL,          -- 'BUS-LVMDP'
  name               TEXT NOT NULL,                 -- 'Busbar LVMDP'
  kind               TEXT NOT NULL CHECK (kind IN ('transformer', 'busbar', 'feeder')),
  warning_pct        DOUBLE PRECISION NOT NULL,     -- ambang warning (%)
  critical_pct       DOUBLE PRECISION NOT NULL,     -- ambang critical (%)
  mismatch_pct       DOUBLE PRECISION NOT NULL DEFAULT -2.0, -- di bawah ini = mismatch
  min_input_kwh      DOUBLE PRECISION NOT NULL DEFAULT 5.0,  -- per jam; di bawahnya % tidak dihitung
  is_active          BOOLEAN NOT NULL DEFAULT TRUE,
  sort_order         INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS balance_node_meters (
  node_id    INTEGER NOT NULL REFERENCES balance_nodes(id) ON DELETE CASCADE,
  device_id  INTEGER NOT NULL REFERENCES devices(id),
  side       TEXT NOT NULL CHECK (side IN ('in', 'out')),
  PRIMARY KEY (node_id, device_id)
);

-- Alarm milik node (bukan milik satu meter).
ALTER TABLE alarms ADD COLUMN IF NOT EXISTS
  balance_node_id INTEGER REFERENCES balance_nodes(id);
```

Seed topologi ditaruh terpisah (`database/init/03-seed-balance.sql`), dengan
node feeder `is_active = FALSE` sampai pemetaannya dikonfirmasi.

Default ambang per jenis (bisa diubah per node):

| `kind` | `warning_pct` | `critical_pct` |
|---|---|---|
| `transformer` | 4 | 6 |
| `busbar` | 3 | 5 |
| `feeder` | 4 | 7 |

Ambang sengaja di atas nilai losses wajar karena akurasi gabungan meter
(kelas 0.5S–1, ditambah error CT) bisa mencapai ±1–2 %.

## 4. Perhitungan

Modul baru: `backend/app/services/balance.py`.

### 4.1 Delta energi per meter

Sumber data: `readings_15min` (permanen, tidak terkena retensi 90 hari).
Delta tiap bucket dihitung dari **selisih counter terakhir bucket ini dengan
counter terakhir bucket sebelumnya** (`lag()`), bukan `last − first` di dalam
bucket. Dengan cara ini, energi di antara dua bucket tidak hilang.

```sql
SELECT device_id, bucket,
       energy_active - lag(energy_active) OVER w AS delta_kwh,
       bucket - lag(bucket) OVER w            AS gap
FROM readings_15min
WHERE device_id = ANY(:ids) AND bucket >= :start - INTERVAL '15 minutes' AND bucket < :end
WINDOW w AS (PARTITION BY device_id ORDER BY bucket);
```

Delta dinyatakan **tidak valid** jika:
- counter `null` di salah satu ujung,
- `gap > 15 menit` (ada bucket bolong / meter offline),
- `delta_kwh < 0` (counter reset atau meter diganti).

### 4.2 Neraca per node per jam

Fungsi murni (mudah di-unit-test, tidak menyentuh DB):

```python
def compute_balance(node, deltas_by_device, hour) -> BalanceRow
```

| Kondisi | `status` |
|---|---|
| Ada meter anggota yang delta-nya tidak valid di jam itu | `invalid` (loss tidak dihitung) |
| `Σ in < min_input_kwh` | `low_load` (kWh tetap ditampilkan, % = `null`) |
| `loss_pct < mismatch_pct` | `mismatch` |
| `loss_pct ≥ critical_pct` | `critical` |
| `loss_pct ≥ warning_pct` | `warning` |
| lainnya | `normal` |

Neraca harian = jumlah jam yang valid. Responsnya menyertakan `coverage`
(jumlah jam valid / 24) agar pengguna tahu seberapa lengkap datanya. Hari
dengan `coverage < 0.9` ditandai *data tidak lengkap* dan tidak dipakai
untuk alarm.

Batas hari mengikuti WIB (`Asia/Jakarta`), sama dengan `daily_energy` dan
`local_day_start`.

> **Catatan resolusi counter:** beberapa meter mungkin hanya mengirim kWh
> dengan resolusi 0,1 atau 1 kWh. Pada node dengan beban kecil, delta per jam
> akan "bergerigi". Karena itu alarm memakai beberapa jam berturut-turut
> (§5), bukan satu jam saja.

## 5. Alarm

Background task baru `balance_watcher()` di `backend/app/main.py`, didaftarkan
di `lifespan` seperti `offline_watcher()`. Task berjalan setiap 15 menit dan
mengevaluasi **jam lengkap** terakhir (jam berjalan tidak ikut dihitung).

| Alarm | Syarat aktif | Syarat pulih |
|---|---|---|
| `energy_loss` (warning/critical) | `loss_pct ≥ warning_pct` selama **3 jam valid berturut-turut** | `loss_pct < warning_pct − 0.5` selama 2 jam valid |
| `energy_mismatch` (warning) | `loss_pct < mismatch_pct` selama 3 jam valid berturut-turut | kembali ≥ `mismatch_pct` selama 2 jam |

Jam `invalid` atau `low_load` tidak menambah maupun memutus hitungan
berturut-turut.

- Alarm disimpan dengan `device_id = NULL` dan `balance_node_id = node.id`,
  sehingga `apply_alarms()` (yang memfilter `device_id`) tidak ikut
  menutupnya.
- Pesan, contoh: `Energi tak terukur Busbar LVMDP 6.2 % (≥ 5 %) selama 3 jam`.
- Alarm critical dikirim ke Telegram lewat mekanisme `notification_state`
  dengan key `balance:<node_code>:<type>`.
- **Perlu disesuaikan:** `list_alarms()` di `services/queries.py` saat ini
  memakai *inner join* ke `devices`, sehingga alarm node akan hilang. Fungsi
  ini harus diubah ke *outer join* ke `devices` dan `balance_nodes`.
  `AlarmOut.device_id` dan `device_name` lalu diisi kode dan nama node.

## 6. API

Router baru: `backend/app/api/balance.py`.

| Endpoint | Isi |
|---|---|
| `GET /api/energy-balance/topology` | Daftar node + meter masuk/keluar (untuk diagram alur) |
| `GET /api/energy-balance?start=&end=&bucket=1h\|1d&node=` | Deret neraca per node: `time, in_kwh, out_kwh, loss_kwh, loss_pct, status, coverage` |
| `GET /api/energy-balance/today` | Ringkasan hari ini per node (kartu di dashboard) |

Batas rentang mengikuti `validate_range()`: `1h` maksimal 31 hari dan `1d`
maksimal 1 tahun.

## 7. Frontend

Halaman baru `frontend/src/app/energy-balance/page.tsx`, ditambahkan ke
`components/layout/sidebar.tsx` dan `mobile-nav.tsx`.

1. **Kartu per node:** kWh masuk, kWh keluar, energi tak terukur (kWh dan %)
   hari ini, badge status, dan indikator coverage.
2. **Diagram alur energi:** memakai komponen `Sankey` dari `recharts` (sudah
   menjadi dependency, tidak perlu paket baru). Lebar aliran = kWh hari ini,
   dan node "Tak terukur" ditampilkan sebagai cabang tersendiri.
3. **Tren loss % harian (30 hari):** garis per node dengan garis putus-putus
   pada ambang warning dan critical.
4. **Tabel per jam (hari terpilih):** baris `invalid` diberi warna abu-abu dan
   alasannya (misal "PM-MCC4-01 offline").

Mode demo: tambahkan fixture neraca di `lib/mock-data.ts`.

## 8. Penyesuaian terkait

1. **Ringkasan total daya/energi (kemungkinan hitung ganda).**
   `get_summary()` menjumlahkan semua meter `role = 'incoming'`, termasuk
   `PM-MVMDP-01`. Jika SLD mengonfirmasi bahwa MVMDP berada di hulu LVMDP
   Incoming 1–5, energi terhitung dua kali. Setelah topologi tersedia, total
   pabrik sebaiknya = jumlah meter sisi `in` pada node yang **tidak menjadi
   sisi `out` node lain** (meter akar).
2. **Simulator.** Nilai nominal di `acquisition/simulator.py` saat ini
   independen per meter (Σ OUT ≠ Σ IN), sehingga neraca di mode simulasi
   tidak bermakna. Simulator perlu menurunkan daya meter hulu dari jumlah
   meter hilir dikali `(1 + loss)`, dengan faktor loss per node yang bisa
   diatur. Faktor ini juga berguna untuk menguji alarm (misalnya
   menyuntikkan loss 8 %).
3. **Dokumentasi.** Tambahkan rumus neraca ke `docs/calculations.md`, dan
   tabel baru ke `docs/data-model.md` serta `schema.dbml`.

## 9. Pertanyaan terbuka

Perlu dijawab dari SLD sebelum implementasi:

1. Apakah `PM-MVMDP-01` memasok LVMDP Incoming 1–5 lewat trafo? Berapa unit
   trafonya?
2. Apakah 5 incoming LVMDP semuanya dari trafo, atau ada genset/PLN terpisah?
3. Outgoing 1, 2, dan 3 masing-masing memasok panel MCC/Pellet yang mana?
4. Apakah ada MCC/Pellet yang dipasok langsung tanpa melewati outgoing yang
   ber-meter?
5. Apakah ada beban besar yang tidak memakai meter (kompresor, penerangan,
   kantor)?
6. Berapa kelas akurasi CT di tiap panel? Nilai ini dipakai untuk
   menyesuaikan ambang default.

## 10. Urutan implementasi

| Tahap | Isi | Bergantung pada |
|---|---|---|
| L1 | Migrasi tabel + seed topologi (feeder nonaktif) | Jawaban §9 no. 1–2 |
| L2 | `services/balance.py` + unit test (`tests/test_balance.py`: normal, offline → invalid, counter reset → invalid, keluar > masuk → mismatch, beban rendah → `low_load`) | L1 |
| L3 | API `/api/energy-balance*` + test query | L2 |
| L4 | Halaman frontend (kartu, Sankey, tren, tabel) + fixture demo | L3 |
| L5 | `balance_watcher` + alarm + Telegram + perbaikan `list_alarms` | L2 |
| L6 | Simulator konsisten-topologi + perbaikan total pabrik (§8.1) | L1, jawaban SLD |
| L7 | Aktifkan node feeder setelah pemetaan dikonfirmasi; kalibrasi ambang dari data 1–2 minggu | Data lapangan |
