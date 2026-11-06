# Backend EMS

FastAPI + PostgreSQL/TimescaleDB + MQTT (Mosquitto) + akuisisi Modbus (`pymodbus`).

## Tanggung jawab

- Worker akuisisi membaca meter (Modbus TCP) atau mode simulator
- Decode register per model (skala, word order, float vs integer)
- Publish JSON engineering ke MQTT
- API subscribe MQTT, hitung PF & kVAh, simpan ke TimescaleDB, evaluasi alarm
- REST + WebSocket untuk frontend

## Struktur

```
backend/
|- app/
|  |- main.py              FastAPI (REST + WebSocket)
|  |- api/                 endpoint
|  |- services/            ingest, MQTT, alarm, query
|  |- acquisition/         pymodbus + profil + decoder
|  |- models.py            SQLAlchemy
|  `- schemas.py           kontrak JSON (camelCase)
|- tests/
|- Dockerfile
|- requirements.txt       dependency runtime (versi dikunci)
`- requirements-dev.txt   + pytest (tidak masuk image)
```

## Endpoint

```
GET  /health
GET  /api/devices
GET  /api/devices/{device_code}
GET  /api/devices/{device_code}/latest
GET  /api/readings?device=&from=&to=&bucket=5m&role=incoming
GET  /api/summary/today
GET  /api/alarms
POST /api/alarms/{id}/acknowledge
WS   /ws
POST /internal/ingest          # debug tanpa MQTT; nonaktif kecuali INGEST_API_KEY diisi (header X-API-Key)
```

`bucket`: `raw` | `1m` | `5m` | `15m` | `1h` | `1d`

Total daya/energi hanya menjumlahkan meter `role=incoming`.

## Menjalankan (Docker, disarankan)

Dari root repo:

```bash
docker compose up --build
```

- API: http://localhost:4000/docs
- Postgres: localhost:5432
- MQTT: localhost:1883

Mode default akuisisi: `simulator` (tidak butuh meter fisik).
Untuk poll meter sungguhan:

```bash
ACQUISITION_MODE=modbus docker compose up --build
```

Sesuaikan `modbus_host` / `modbus_address` di tabel `devices`.

Histori simulasi 30 hari (interval 15 menit, termasuk per fasa) **tidak lagi
dimuat otomatis** agar tidak tercampur dengan data meter asli. Untuk mengisinya
secara manual pada database pengembangan, jalankan dari root repository:

```bash
docker compose exec -T db psql -U ems -d ems -v ON_ERROR_STOP=1 < scripts/seed-history.sql
docker compose up --build -d acquisition
```

Skrip tersebut hanya untuk demo/pengembangan; jangan jalankan pada database
produksi atau database yang menyimpan data meter sungguhan. Ganti `ems` pada
perintah jika nama user/database di `.env` berbeda.

## Menjalankan lokal tanpa Docker API

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 4000
python -m app.acquisition
```

Database dan Mosquitto tetap lewat `docker compose up db mqtt`. Broker MQTT
wajib login, jadi set `MQTT_USERNAME` dan `MQTT_PASSWORD` (default compose:
`ems` / `ems-mqtt`; ganti di `.env`).

## Error log dan notifikasi Telegram

Error backend, database, MQTT, akuisisi/Modbus, dan koneksi API dari frontend
dicatat ke log container. Error baru mengirim satu pesan Telegram, lalu satu
pesan pemulihan setelah sistem mendeteksi koneksi normal kembali. Pengiriman
Telegram bersifat opsional; tanpa kredensial, pencatatan log tetap aktif.

1. Buat bot melalui BotFather, kirim `/start` ke bot, lalu dapatkan chat ID.
2. Simpan konfigurasi berikut di `.env` pada root project. Jangan commit token:

   ```dotenv
   TELEGRAM_BOT_TOKEN=token-dari-botfather
   TELEGRAM_CHAT_ID=id-chat-telegram
   ```

3. Terapkan konfigurasi dengan menjalankan `docker compose up --build -d`.
4. Lihat log sewaktu-waktu dengan:

   ```powershell
   docker compose logs -f backend acquisition
   ```

Aturan notifikasi:

- **Meter offline** hanya dilaporkan oleh backend (berdasarkan data terakhir
  > 3 menit). Acquisition hanya mencatat log, sehingga satu kejadian = satu pesan.
- **Alarm kelistrikan critical** (PF, tegangan, frekuensi, THD, unbalance,
  beban) dikirim dengan judul `EMS ALARM KRITIS`, dan `EMS ALARM PULIH` saat
  alarm normal kembali atau turun ke warning. Alarm warning tidak dikirim.
- Status notifikasi aktif disimpan di tabel `notification_state`, sehingga
  restart service tidak mengirim ulang error yang sama.
- Alarm baru aktif bila kondisi bertahan `ALARM_ON_DELAY_SECONDS` (default 30)
  dan baru normal bila nilai keluar dari deadband selama
  `ALARM_OFF_DELAY_SECONDS` (default 30).

Peringatan koneksi dari browser dikirim best-effort. Jika backend sepenuhnya
tidak dapat dijangkau, browser tidak bisa meneruskan error ke Telegram; error
tersebut tetap terlihat di console browser. Kegagalan proses/container yang
berhenti total juga memerlukan pemantau eksternal untuk memberi notifikasi.

## Tes

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```
