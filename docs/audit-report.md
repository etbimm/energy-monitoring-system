# Laporan Audit Project EMS

## Ringkasan eksekutif

Audit read-only ini meninjau source code, konfigurasi, dokumentasi, dan tes
Energy Monitoring System, lalu menjalankan validasi lokal yang aman. Area
prioritas sebelum penggunaan operasional adalah:

1. Mengamankan kredensial bawaan, port layanan, dan transport HTTP.
2. Membatasi otorisasi broker MQTT dan memvalidasi telemetry yang masuk.
3. Memastikan topologi meter sebelum memperlakukan total energi sebagai angka
   operasional.
4. Memperbaiki pembatasan percobaan login, ketahanan consumer MQTT, dan quality
   gates.

Temuan di bawah adalah hasil inspeksi source dan konfigurasi yang tersedia.
Risiko deployment yang bergantung pada `.env`, firewall, topologi listrik, atau
lingkungan produksi ditandai sebagai bersyarat dan perlu dikonfirmasi.

## Cakupan dan batas audit

- Tidak ada host, perangkat meter, atau sistem produksi yang diuji.
- Isi `.env`, backup database, dan kredensial aktual tidak dibaca.
- Tes dan pemeriksaan frontend hanya dijalankan secara lokal.
- Tidak ada perubahan kode aplikasi; perubahan staged yang telah ada pada
  `docker-compose.yml` dipertahankan.
- Pemeriksaan migrasi/tooling/CI/Compose, build frontend, dan pencarian lokasi
  workspace canvas tidak dapat diselesaikan karena pembatasan izin yang
  dijelaskan di bagian [Validasi dan keterbatasan](#validasi-dan-keterbatasan).

## Temuan terprioritas

### 1. Kredensial layanan bawaan dan port host yang dipublikasikan

**Prioritas: Tinggi bila Compose digunakan pada host yang dapat dijangkau jaringan**

**Bukti**

- Compose menyediakan password PostgreSQL default `ems`:
  [docker-compose.yml](../docker-compose.yml#L7).
- Kredensial default MQTT adalah `ems` / `ems-mqtt`:
  [docker-compose.yml](../docker-compose.yml#L24).
- Port PostgreSQL dipetakan ke host:
  [docker-compose.yml](../docker-compose.yml#L10).
- Port MQTT dipetakan ke host:
  [docker-compose.yml](../docker-compose.yml#L44).

**Dampak**

Jika deployment menggunakan fallback tersebut dan host dapat diakses dari
jaringan lain, kredensial yang diketahui dapat membuka akses ke database atau
broker. Pemetaan port memperluas permukaan akses; jangkauan aktual bergantung
pada konfigurasi host dan firewall. Nilai `.env` aktual tidak diperiksa.

**Rekomendasi**

- Hilangkan kredensial default untuk deployment production dan gagalkan startup
  bila secret wajib tidak diberikan.
- Gunakan secret kuat yang unik dan rotasi kredensial yang pernah dibagikan.
- Jangan publikasikan port database/broker ke jaringan umum; gunakan jaringan
  internal atau bind loopback bila akses host memang diperlukan.
- Batasi koneksi dengan firewall dan dokumentasikan konfigurasi production
  secara terpisah dari mode development.

### 2. MQTT tidak memiliki ACL per topic dan ingest mempercayai `device_code`

**Prioritas: Tinggi**

**Bukti**

- Mosquitto memerlukan autentikasi password, tetapi konfigurasi yang ditinjau
  tidak menetapkan ACL:
  [mosquitto.conf](../mqtt/mosquitto.conf#L1).
- Backend subscribe ke wildcard telemetry:
  [mqtt.py](../backend/app/services/mqtt.py#L21).
- Identitas meter diambil dari payload dan diteruskan ke ingest:
  [mqtt.py](../backend/app/services/mqtt.py#L51) dan
  [ingest.py](../backend/app/services/ingest.py#L67).
- Ingest tidak menerima atau memeriksa topic MQTT sebagai pembanding identitas
  meter:
  [ingest.py](../backend/app/services/ingest.py#L67).

**Dampak**

Klien yang memiliki kredensial broker berpotensi menerbitkan telemetry atas
nama device aktif lain, lalu memengaruhi histori, status, dan alarm. Dampaknya
bergantung pada keterjangkauan broker dan distribusi kredensial.

**Rekomendasi**

- Terapkan ACL least-privilege dan kredensial berbeda untuk acquisition dan
  backend (misalnya acquisition hanya publish, backend hanya subscribe).
- Cocokkan device pada topic dengan `device_code` payload.
- Validasi payload sebagai object dengan field dan tipe yang diizinkan sebelum
  mengubah database.
- Tolak nilai numerik non-finite serta timestamp yang terlalu jauh di masa
  depan/lampau; tetapkan batas kewajaran sesuai karakteristik meter.
- Aktifkan TLS bila broker diakses lintas host/jaringan.

### 3. Cookie sesi tidak Secure secara default; akses HTTP masih digunakan

**Prioritas: Tinggi bila aplikasi diakses melalui jaringan tanpa TLS**

**Bukti**

- `cookie_secure` default `False`:
  [config.py](../backend/app/config.py#L37).
- Compose juga memberi default `COOKIE_SECURE=false`:
  [docker-compose.yml](../docker-compose.yml#L74).
- Atribut cookie `Secure` mengikuti pengaturan tersebut:
  [auth.py](../backend/app/api/auth.py#L40).

**Dampak**

Pada akses HTTP, password login dan cookie sesi dapat terekspos kepada pihak
yang dapat mengamati atau memanipulasi lalu lintas jaringan. `HttpOnly` dan
`SameSite` tidak mengenkripsi lalu lintas.

**Rekomendasi**

- Wajibkan HTTPS untuk seluruh akses production dan set `COOKIE_SECURE=true`.
- Terminasi TLS pada reverse proxy yang terkelola, batasi akses langsung ke
  port backend, dan tambahkan konfigurasi header keamanan yang sesuai.
- Pastikan dokumentasi deployment membedakan URL lokal HTTP dari URL
  production HTTPS.

### 4. Total energi/daya dapat double-count jika meter incoming bertingkat

**Prioritas: Tinggi bersyarat; konfirmasi sebelum memakai total untuk laporan operasional**

**Bukti**

- Ringkasan daya menjumlahkan semua baris dengan `role == "incoming"`:
  [queries.py](../backend/app/services/queries.py#L430).
- Rancangan energy balance menyebut topologi MVMDP/LVMDP masih asumsi dan
  memperingatkan potensi penghitungan ganda:
  [loss-detection-design.md](./loss-detection-design.md).

**Dampak**

Jika suatu meter incoming berada di sisi hulu meter incoming lain, penjumlahan
semua meter tersebut akan menghitung energi yang sama lebih dari sekali.
Apakah hal ini terjadi belum dapat dipastikan tanpa single-line diagram (SLD)
dan konfirmasi inventaris listrik.

**Rekomendasi**

- Konfirmasi SLD, sumber tiap panel, meter yang mewakili batas pabrik, dan
  keberadaan sumber lain (misalnya genset/PV).
- Tetapkan aturan agregasi berdasarkan meter akar/topologi yang disetujui,
  bukan hanya role bebas.
- Tambahkan tes rekonsiliasi terhadap kasus meter hulu-hilir sebelum merilis
  perubahan total.

### 5. Login throttle dapat mempertahankan key tanpa batas

**Prioritas: Sedang**

**Bukti**

- Throttle menyimpan bucket kegagalan per kombinasi IP dan username:
  [auth.py](../backend/app/services/auth.py#L110).
- Saat jumlah key melewati 10.000, pembersihan hanya menghapus bucket kosong:
  [auth.py](../backend/app/services/auth.py#L139).
- Reproduksi lokal tanpa jaringan dengan 10.001 username unik menghasilkan
  10.001 key tetap tersimpan.

**Dampak**

Permintaan login gagal dengan identitas bervariasi dapat menumbuhkan memori
proses. Limit per pasangan IP/username juga dapat dilewati dengan mengganti
salah satu nilai; penyimpanan in-memory tidak konsisten antar worker dan reset
saat proses restart.

**Rekomendasi**

- Purge bucket yang seluruh kegagalannya sudah kedaluwarsa secara berkala,
  bukan hanya saat pasangan yang sama diminta lagi.
- Terapkan batas global jumlah key dan aturan eviction yang terukur.
- Gabungkan limit per-IP, per-akun, dan global; gunakan penyimpanan bersama
  (misalnya Redis) bila deployment multi-worker.
- Tambahkan tes untuk banyak username unik, expiry, batas kapasitas, serta
  konsistensi antar proses.

### 6. Payload MQTT malformed dapat menghentikan consumer

**Prioritas: Sedang**

**Bukti**

- Decode payload hanya menangani `JSONDecodeError`:
  [mqtt.py](../backend/app/services/mqtt.py#L40).
- Kode kemudian memanggil `.get()` pada hasil JSON tanpa memastikan bahwa
  nilainya object:
  [mqtt.py](../backend/app/services/mqtt.py#L51).
- Jalur reconnect luar menangani `MqttError`; exception decode/type lain dari
  jalur pesan tidak dipulihkan sebagai kegagalan pesan individual:
  [mqtt.py](../backend/app/services/mqtt.py#L38).

**Dampak**

Byte non-UTF-8 dapat gagal pada decode; JSON valid seperti `null` atau array
dapat gagal saat `.get()`. Satu pesan semacam ini berpotensi mengakhiri task
subscriber dan menghentikan ingest hingga backend dimulai ulang.

**Rekomendasi**

- Tangani `UnicodeDecodeError`, kesalahan JSON, dan kesalahan skema per pesan.
- Pastikan payload adalah object sebelum membaca field; catat penolakan tanpa
  membiarkan satu pesan menghentikan subscriber.
- Tambahkan tes untuk payload non-UTF-8, JSON invalid, `null`, array, field
  hilang, dan device tidak dikenal.
- Pantau liveness subscriber/task pada health check, bukan hanya status koneksi
  MQTT terakhir.

### 7. Tes dan quality gate belum selaras dengan kontrak implementasi

**Prioritas: Sedang**

**Bukti**

- `test_registry_integrity` mengharapkan himpunan model kVAh yang tidak
  mencakup CEWE Elite440:
  [test_decoder.py](../backend/tests/test_decoder.py#L87).
- Profil CEWE menyatakan kVAh tersedia:
  [profiles.py](../backend/app/acquisition/profiles.py#L147).
- Tes simulator mengharapkan PAC3220 hanya menyediakan tegangan L-L:
  [test_simulator.py](../backend/tests/test_simulator.py#L26).
- Dokumentasi perhitungan juga menyebut PAC3220 hanya L-L:
  [calculations.md](./calculations.md#L41), sementara profil register yang
  ditinjau mendefinisikan register tegangan L-N dan L-L.
- Perintah lint yang tersedia adalah `next lint`:
  [package.json](../frontend/package.json#L10); saat dijalankan, perintah
  meminta konfigurasi ESLint secara interaktif.

**Dampak**

Suite saat ini gagal pada kontrak kapabilitas meter dan tidak memberi sinyal
bersih untuk regresi. Perbedaan PAC3220 berpotensi menunjukkan ketidakselarasan
antara peta register, simulator, tes, dan dokumentasi; fakta meter perlu
diverifikasi terhadap manual/commissioning sebelum memilih sumber kebenaran.
Lint tidak dapat menjadi quality gate otomatis selama masih interaktif.

**Rekomendasi**

- Verifikasi kVAh dan register tegangan terhadap manual model/varian yang benar.
- Selaraskan profil runtime, simulator, ekspektasi tes, dan dokumentasi setelah
  keputusan tersebut dikonfirmasi.
- Konfigurasikan ESLint secara non-interaktif dan tambahkan lint/typecheck/test
  ke CI. Status konfigurasi/workflow CI sendiri belum berhasil diverifikasi
  dalam audit ini.

## Validasi dan keterbatasan

### Hasil yang berhasil dijalankan

- Backend `python -m pytest -q`: **159 lulus, 2 gagal**.
  - `test_registry_integrity` gagal karena ekspektasi daftar model kVAh tidak
    selaras dengan kapabilitas CEWE di profil.
  - `test_simulator_sends_only_voltage_registers_of_the_model` gagal karena
    ekspektasi PAC3220 L-L saja tidak selaras dengan profil tegangan runtime;
    dokumentasi juga perlu dikonfirmasi terhadap manual meter.
- Frontend TypeScript (`tsc --noEmit --incremental false`): **lulus**.
- `npm run lint`: berhenti pada prompt konfigurasi ESLint; **lint tidak selesai**
  dan tidak dinyatakan lulus.

### Aksi yang diblokir

1. **Pemeriksaan migrasi/tooling/CI/Compose:** command pemeriksaan ditolak
   karena tahap `docker compose config` dapat membaca `.env`. Tidak dicoba
   ulang atau diakali; status migrasi/tooling/CI dan konfigurasi Compose hasil
   render belum diverifikasi.
2. **Build frontend:** build menulis artifact dan aksi tersebut tidak
   diizinkan. Tidak dicoba ulang; build produksi belum diverifikasi.
3. **Pencarian workspace canvas:** pencarian lokasi di luar cakupan repository
   dan pemeriksaan lokal ditolak. Tidak dicoba ulang atau diakali. Hasil
   disediakan sebagai dokumen Markdown sesuai permintaan.

Validasi di atas tidak mencakup pengujian meter fisik, broker/database yang
sedang berjalan, atau deployment production.

## Urutan tindak lanjut yang disarankan

1. Hilangkan kredensial production default, batasi port, dan wajibkan HTTPS
   serta cookie Secure.
2. Terapkan ACL dan kredensial MQTT per service; validasi topic, identitas,
   timestamp, dan payload.
3. Konfirmasi SLD dan uji rekonsiliasi total energi/daya.
4. Perbaiki batas memori/rate limit login dan ketahanan subscriber MQTT.
5. Selaraskan tes dengan spesifikasi meter yang dikonfirmasi, lalu aktifkan
   quality gates non-interaktif di CI.
