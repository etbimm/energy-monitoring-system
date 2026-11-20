# EMS - Energy Monitoring System

Dashboard monitoring energi untuk 18 power meter di Java Wood Pellet.

## Alur Data

```
Power Meter (Modbus RTU / TCP)
  -> RS485 to Ethernet Converter (meter RS485)
  -> Switch / Network
  -> Acquisition (Python + pymodbus, decode per model)
  -> MQTT Broker (Mosquitto)
  -> Backend API (FastAPI) + PostgreSQL/TimescaleDB
  -> Frontend Dashboard (Next.js)
```

## Struktur Folder

```
ems/
|- frontend/     Dashboard Next.js (REST API + WebSocket)
|- backend/      FastAPI + worker akuisisi Modbus
|- database/     SQL init PostgreSQL/TimescaleDB
|- mqtt/         Konfigurasi Mosquitto
|- docs/         Dokumentasi arsitektur & data model
`- scripts/      Utilitas
```

## Menjalankan Backend + Database + MQTT

```bash
docker compose up --build
```

| Service | URL |
|---|---|
| API + Swagger | http://localhost:4000/docs |
| PostgreSQL | localhost:5432 (user/db `ems`) |
| MQTT | localhost:1883 (wajib login: `MQTT_USERNAME`/`MQTT_PASSWORD`, default `ems`/`ems-mqtt`) |

Mode akuisisi default: `simulator` (tanpa hardware). Set `ACQUISITION_MODE=modbus` di `.env` untuk poll meter sungguhan.

## Login dan Hak Akses

Semua halaman dashboard dan endpoint data wajib login. Akun dibuat oleh admin
(tidak ada registrasi publik). Ada dua role:

| Fitur | Viewer | Admin |
|---|:-:|:-:|
| Overview, Real-time, History, Power Quality, Devices, Alarms (lihat) | ✅ | ✅ |
| Acknowledge alarm | ❌ | ✅ |
| Kelola akun (tambah, ubah role, nonaktifkan, hapus, reset password) | ❌ | ✅ |
| Kelola device (tambah, edit, nonaktifkan) | ❌ | ✅ |
| Audit log | ❌ | ✅ |
| Ganti password sendiri | ✅ | ✅ |

1. Isi `JWT_SECRET` di `.env` (string acak >= 32 karakter). `docker compose`
   menjalankan backend dengan `ENVIRONMENT=production`, sehingga backend akan
   **gagal start** bila `JWT_SECRET` kosong atau kurang dari 32 karakter. Untuk
   pengembangan lokal tanpa secret, set `ENVIRONMENT=development`.
   Lalu jalankan `docker compose up -d --build backend`.
2. Buat admin pertama (password diketik di terminal, tidak tersimpan di repo):

   ```bash
   docker compose exec backend python -m app.cli create-admin
   ```

3. Login di dashboard, lalu buat akun lain lewat menu **Admin > Kelola Akun**.

Lupa password admin: `docker compose exec backend python -m app.cli reset-password --username <nama>`.

Sesi disimpan sebagai JWT di cookie httpOnly (`SameSite=Lax`). Karena itu
**frontend dan backend harus diakses lewat host yang sama** (mis. keduanya
`localhost`, atau keduanya `192.168.1.10`). Bila `NEXT_PUBLIC_API_URL` tidak
diisi, frontend otomatis memakai host halaman dengan port 4000. Akses dari
perangkat lain di LAN juga butuh origin tersebut di `CORS_ORIGINS`.

Device yang dinonaktifkan tidak lagi dibaca akuisisi (paling lambat 60 detik)
dan tidak tampil di dashboard, tetapi riwayat datanya tetap tersimpan.

Model meter di luar daftar bisa ditambahkan lewat pilihan **Lainnya** (isi merek
dan nama model). Model seperti ini belum punya peta register Modbus, sehingga
belum terbaca di mode `modbus` dan tampil offline (ditandai "Belum didukung").
Agar terbaca, tambahkan profilnya di `backend/app/acquisition/profiles.py`
(`PROFILES` dan `MODEL_CATALOG`) dengan nama model yang sama persis.

Kolom **Peran** dan **Jalur** juga punya pilihan **Lainnya**. Hanya peran
`Incoming` yang dihitung ke total daya dan energi pabrik; peran lain (mis.
Genset, Solar PV) tampil di dashboard tetapi tidak ikut total. Jalur hanya
informasi: akuisisi selalu membaca lewat Modbus TCP ke Host:Port device.

## Menjalankan Frontend

```bash
cd frontend
npm install
npm run dev
```

Buka http://localhost:3000

Frontend mengambil data dari API backend. Secara default API URL adalah
`http://localhost:4000`; atur `NEXT_PUBLIC_API_URL` sebelum menjalankan
frontend jika backend berada di host/port lain. WebSocket menggunakan URL yang
sama dengan skema `ws://`; atur `NEXT_PUBLIC_WS_URL` hanya jika endpoint WS
berbeda. Jika backend belum tersedia atau belum memiliki data meter, dashboard
menampilkan pesan error dan **tidak** menampilkan angka palsu.

Untuk presentasi tanpa backend sama sekali, aktifkan data mock frontend secara
eksplisit dengan `NEXT_PUBLIC_DEMO_MODE=true` (ditandai **Mode demo** di UI).
Untuk data dummy yang mengalir lewat backend, gunakan `ACQUISITION_MODE=simulator`.

## Migrasi Database

File di `database/init/` hanya dijalankan saat volume database pertama kali
dibuat. Untuk database yang sudah berjalan, jalankan file di
`database/migrations/` yang belum pernah diterapkan secara berurutan, misalnya:

```bash
docker exec -i ems-db-1 psql -U ems -d ems < database/migrations/001-daily-energy-wib.sql
docker exec -i ems-db-1 psql -U ems -d ems < database/migrations/002-notification-state.sql
docker exec -i ems-db-1 psql -U ems -d ems < database/migrations/003-aggregates-compression-retention.sql
docker exec -i ems-db-1 psql -U ems -d ems < database/migrations/004-auth-device-management.sql
docker exec -i ems-db-1 psql -U ems -d ems < database/migrations/005-device-role-transport-lainnya.sql
docker exec -i ems-db-1 psql -U ems -d ems < database/migrations/006-alarm-settings.sql
```

Migrasi SQL `001`–`006` adalah riwayat legacy dan tidak boleh dijalankan ulang
pada database yang sudah menerapkannya. Setelah skema database mencapai versi
tersebut, aktifkan pencatatan Alembic (revisi baseline ini tidak mengubah skema):

```bash
docker compose exec backend alembic upgrade head
```

Migrasi skema baru selanjutnya dibuat dan ditinjau sebagai revisi Alembic.
Untuk menghasilkan revisi dari dalam container sekaligus menyimpan berkasnya
ke workspace:

```bash
docker compose run --rm -v ./backend:/app backend alembic revision --autogenerate -m "deskripsi perubahan"
```

Tinjau dan lengkapi revisi, terutama untuk objek TimescaleDB yang tidak selalu
dapat dideteksi autogenerate, lalu terapkan dengan
`docker compose exec backend alembic upgrade head`. Jangan mengubah urutan atau
menghapus revisi yang sudah diterapkan.

Kebijakan penyimpanan: data mentah (`readings`, `phase_readings`) dikompresi
setelah 7 hari dan dihapus setelah 90 hari. Grafik dan total energi dibaca dari
continuous aggregate yang disimpan permanen. Rentang energi pendek menggunakan
`readings_1min`; rentang tanggal panjang menggunakan `daily_energy` untuk hari
lengkap terbaru dan `readings_15min` untuk tepi rentang / energi semu. Query raw
dibatasi 7 hari dan setiap respons time series maksimal 20.000 titik.

## Status

- [x] Struktur monorepo
- [x] Frontend scaffold dengan mock data
- [x] Backend API FastAPI
- [x] PostgreSQL + TimescaleDB
- [x] MQTT broker (Mosquitto)
- [x] Akuisisi pymodbus + profil decode per model
- [x] Integrasi dashboard ke API (REST + WebSocket)
- [x] Histori API, tabel pembacaan, dan export CSV
- [x] Acknowledge alarm dari dashboard

## Dokumentasi

- [Arsitektur](docs/architecture.md)
- [Data Model](docs/data-model.md)
- [Spesifikasi Parameter](docs/parameter-specification.md)
- [Inventaris Perhitungan](docs/calculations.md)
- [Dokumen UAT](docs/UAT.md)
- [Flowchart Program Utama](docs/program-flowchart.md)
- [User Role Diagram & Matriks Hak Akses](docs/user-role.md)
- [Backend](backend/README.md)
