# Data Model

> Untuk daftar parameter lengkap, matriks kapabilitas per model meter, dan
> tabel register: [`parameter-specification.md`](./parameter-specification.md).
> Acuan parsing runtime: [`../backend/app/acquisition/profiles.py`](../backend/app/acquisition/profiles.py).

## Parameter Power Meter

Parameter dibagi 3 lapis (detail & alasan di `parameter-specification.md`):

| Lapis | Parameter | Sumber |
|---|---|---|
| **Inti** | V, I, kW, kVA, kVAR, kWh, kVARh, Hz | polled dari meter |
| **Turunan** | PF, kVAh | dihitung backend: `PF = kW/kVA`, `kVAh = kWh/PF` |
| **Opsional** | THD-I, THD-U, unbalance V/I | polled, `NULL` bila tidak didukung |

> **kVAh dan PF tidak pernah dipoll** — hanya 1 dari 5 model meter yang punya
> register kVAh, dan definisi register PF berbeda antar model.

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
| role | TEXT | incoming / outcoming / distribution |
| modbus_host | TEXT | IP meter atau RS485-to-Ethernet converter |
| modbus_address | INT | slave id Modbus |
| transport | TEXT | rs485 / ethernet |
| capabilities | JSONB | kapabilitas efektif unit ini (per unit, bukan per model) |
| is_active | BOOLEAN | masih dipakai atau tidak |

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
| device_id | INT FK | |
| severity | TEXT | critical / warning / info |
| message | TEXT | |
| acknowledged | BOOLEAN | sudah di-ack oleh operator |
| triggered_at | TIMESTAMPTZ | |

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
| Raw | 5 detik | 7 hari | real-time, deteksi anomali |
| Intraday | 1 menit | 90 hari | grafik shift, laporan harian |
| Aggregate | 15 menit | 2 tahun | grafik mingguan/bulanan |
| Rollup | harian | ∞ | laporan, basis penalti PF |

> Fitur estimasi biaya **tidak** diimplementasikan (permintaan pemilik proyek).
> Data PF & kVARh tetap dikumpulkan karena berguna untuk pengajuan penalti PF
> ke PLN.
