# Data Model

> Untuk daftar parameter lengkap, matriks kapabilitas per model meter, dan
> tabel register: [`parameter-specification.md`](./parameter-specification.md).
> Acuan parsing runtime: [`../backend/app/acquisition/profiles.py`](../backend/app/acquisition/profiles.py).

## Parameter Power Meter

Parameter dibagi 3 lapis (detail & alasan di `parameter-specification.md`):

| Lapis | Parameter | Sumber |
|---|---|---|
| **Inti** | V, I, kW, kVA, kVAR, kWh, kVARh, Hz | polled dari meter |
| **Turunan** | PF; kVAh bila tidak ada counter native | PF dihitung backend; kVAh diintegrasikan dari kWh/PF kecuali ELITE440 yang memakai counter native |
| **Opsional** | THD-I, THD-U, unbalance V/I | polled, `NULL` bila tidak didukung |

> PF tidak pernah dipoll karena definisi register berbeda antar model. ELITE440
> mempoll counter kVAh native; counter native pada PAC3220, DMG510, dan EM220
> belum dipoll.

Skala register per model ada di [`../backend/app/acquisition/profiles.py`](../backend/app/acquisition/profiles.py).
Ringkasnya: PAC3220 & Elite440 = IEEE754 float, sisanya integer berskala
(10 / 100 / 1000 — berbeda per model).

## Tabel

### devices

| Kolom | Tipe | Keterangan |
|---|---|---|
| id | SERIAL PK | id internal |
| device_code | TEXT UNIQUE | kode meter, mis PM-LVMDP-IN-01 |
| name | TEXT | nama tampilan |
| location | TEXT | lokasi / zona (LVMDP, MCC 1, MCC Pellet 2, ...) |
| brand | TEXT | merk power meter |
| model | TEXT | SIEMENS PAC3220 / LOVATO DMG510 / CEWE Elite440 / ACREL AMC96 / WEIDMULLER EM220 |
| role | TEXT | incoming / outcoming / distribution, atau peran "Lainnya" (maks 40 karakter). Hanya `incoming` yang dihitung ke total pabrik |
| modbus_host | TEXT | IP meter atau RS485-to-Ethernet converter |
| modbus_port | INT | port Modbus TCP (default 502) |
| modbus_address | INT | slave id Modbus |
| transport | TEXT | rs485 / ethernet, atau jalur "Lainnya" (informasi; akuisisi selalu Modbus TCP ke host:port) |
| capabilities | JSONB | kapabilitas efektif unit ini (per unit, bukan per model) |
| rated_power_kw | DOUBLE | kapasitas nominal untuk evaluasi alarm beban |
| is_active | BOOLEAN | masih dipakai atau tidak (nonaktif = tidak dibaca & tidak tampil, riwayat tetap) |
| last_seen_at | TIMESTAMPTZ | waktu telemetry terakhir; dipakai untuk status dan alarm offline |
| created_at / updated_at | TIMESTAMPTZ | waktu pembuatan dan perubahan terakhir |

Alamat Modbus `(modbus_host, modbus_port, modbus_address)` unik di antara
device aktif (index `uq_devices_modbus_active`). Device tidak pernah dihapus
permanen karena `readings` dan `alarms` mereferensikannya.

### readings (hypertable)

| Kolom | Tipe | Lapis | Keterangan |
|---|---|---|---|
| time | TIMESTAMPTZ PK | | waktu pembacaan |
| device_id | INT FK | | refer ke devices |
| voltage | DOUBLE | inti | Volt |
| current | DOUBLE | inti | Ampere |
| power | DOUBLE | inti | kW |
| apparent_power | DOUBLE | inti | kVA |
| reactive_power | DOUBLE | inti | kVAR |
| energy_active | DOUBLE | inti | kWh kumulatif dari meter |
| energy_reactive | DOUBLE | inti | kVARh kumulatif dari meter |
| frequency | DOUBLE | inti | Hz |
| power_factor | DOUBLE | **turunan** | 0..1, = power / apparent_power |
| energy_apparent | DOUBLE | **turunan** | kVAh kumulatif, = energy_active / power_factor |
| thd_current | DOUBLE NULL | opsional | % THD arus |
| thd_voltage | DOUBLE NULL | opsional | % THD tegangan |
| unbalance_voltage | DOUBLE NULL | opsional | % |
| unbalance_current | DOUBLE NULL | opsional | % |

Partition: 1 hari per chunk. Index `(device_id, time DESC)`.

### phase_readings (hypertable)

| Kolom | Tipe | Keterangan |
|---|---|---|
| time | TIMESTAMPTZ PK | waktu pembacaan |
| device_id | INT FK | refer ke devices |
| phase | TEXT | L1 / L2 / L3 |
| voltage | DOUBLE | Volt |
| current | DOUBLE | Ampere |
| power | DOUBLE | kW |
| apparent_power | DOUBLE | kVA |
| reactive_power | DOUBLE | kVAR |
| power_factor | DOUBLE | 0..1 |
| thd_current | DOUBLE NULL | % |
| thd_voltage | DOUBLE NULL | % |

> Dipisah dari `readings` karena hanya sebagian meter yang mengukur per fasa
> dan volumenya 3× lebih besar.

### alarms

| Kolom | Tipe | Keterangan |
|---|---|---|
| id | SERIAL PK | |
| device_id | INT FK NULL | meter terkait; NULL diperbolehkan untuk alarm tanpa meter |
| alarm_type | TEXT | jenis alarm |
| severity | TEXT | critical / warning / info |
| message | TEXT | |
| acknowledged | BOOLEAN | sudah di-ack oleh operator |
| acknowledged_at | TIMESTAMPTZ NULL | waktu acknowledge |
| triggered_at | TIMESTAMPTZ | |
| cleared_at | TIMESTAMPTZ NULL | waktu kondisi pulih |

### alarm_settings

| Kolom | Tipe | Keterangan |
|---|---|---|
| id | INT PK | satu baris pengaturan aktif (id = 1) |
| thresholds | JSONB | ambang alarm yang dapat diubah admin |
| updated_at | TIMESTAMPTZ | waktu perubahan terakhir |

### users

| Kolom | Tipe | Keterangan |
|---|---|---|
| id | SERIAL PK | |
| username | TEXT UNIQUE | huruf kecil, angka, `.`, `_`, `-` (3-32 karakter) |
| password_hash | TEXT | hash Argon2 (password tidak pernah disimpan apa adanya) |
| full_name | TEXT | nama tampilan |
| role | TEXT | `admin` / `viewer` |
| is_active | BOOLEAN | akun nonaktif tidak bisa login |
| token_version | INT | dinaikkan saat password direset, role diubah, atau akun dinonaktifkan; sesi lama langsung tidak berlaku |
| last_login_at | TIMESTAMPTZ | |
| created_at / updated_at | TIMESTAMPTZ | |

### audit_log

| Kolom | Tipe | Keterangan |
|---|---|---|
| id | BIGSERIAL PK | |
| user_id | INT FK users | pelaku (NULL bila lewat CLI / login gagal) |
| username | TEXT | salinan username pelaku saat kejadian |
| action | TEXT | mis. `auth.login`, `auth.login_failed`, `user.create`, `device.update`, `device.deactivate` |
| target | TEXT | username / kode device yang dikenai aksi |
| detail | JSONB | perubahan `{field: {from, to}}` atau info tambahan (IP) |
| created_at | TIMESTAMPTZ | |

### notification_state

| Kolom | Tipe | Keterangan |
|---|---|---|
| key | TEXT PK | kunci notifikasi aktif |
| summary | TEXT | ringkasan error/alarm yang sudah dilaporkan |
| active_since | TIMESTAMPTZ | waktu notifikasi menjadi aktif |

## Aturan Alarm (contoh, sesuaikan)

| Parameter | Ambang Warning | Ambang Critical | Berlaku untuk |
|---|---|---|---|
| Power factor | < 0.90 | < 0.85 | semua meter |
| Tegangan | di luar 385-415 V | di luar 350-440 V | semua meter |
| Frekuensi | deviasi > 0.5 Hz dari 50 Hz | deviasi > 1.0 Hz | semua meter |
| THD-I | ≥ 5% | ≥ 8% | meter dengan dukungan THD |
| Unbalance tegangan | > 2% | > 5% | meter dengan dukungan unbalance |
| Offline | heartbeat > 30 detik | > 3 menit | semua meter |
| Beban | > 80% kapasitas | > 95% kapasitas | semua meter |

## Agregasi & Energy Delta

### Hindari double counting

Energi melewati beberapa meter (LVMDP Incoming → Outcoming → MCC). Total sistem
hanya menghitung meter ber-role `incoming` (LVMDP Incoming + MVMDP).

```
total_power  = Σ power         untuk role = 'incoming'
total_energy = Σ energy_active untuk role = 'incoming'
```

Meter `outcoming` dan `distribution` ditampilkan sebagai rincian per panel,
tidak dijumlahkan ke total.

### Energy: delta, bukan absolut

Register energy bersifat kumulatif. Untuk energi interval:

```
energy_interval = energy_sekarang - energy_sebelumnya
```

Bila `energy_sekarang < energy_sebelumnya` → overflow 32-bit atau reset meter.
Tandai interval invalid, jangan simpan sebagai angka negatif.

## Strategi Retensi

| Tingkat | Interval | Retensi | Dipakai untuk |
|---|---|---|---|
| Raw | 5 detik | kompresi 7 hari; retensi 90 hari | real-time, deteksi anomali |
| Intraday | 1 menit | ∞ | grafik shift, query historis |
| Aggregate | 15 menit | ∞ | rentang energi panjang dan query historis |
| Rollup | harian | ∞ | energi harian, laporan |

Data mentah `readings` dan `phase_readings` dikompresi setelah 7 hari dan
dihapus setelah 90 hari. Continuous aggregate 1 menit, 15 menit, dan harian
tidak memiliki kebijakan retensi.

> Fitur estimasi biaya **tidak** diimplementasikan (permintaan pemilik proyek).
> Data PF & kVARh tetap dikumpulkan karena berguna untuk pengajuan penalti PF
> ke PLN.
