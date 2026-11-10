# User Acceptance Test (UAT) - Energy Monitoring System

## 1. Informasi Pengujian

| Informasi | Isi |
|---|---|
| Nama sistem | Energy Monitoring System (EMS) - Java Wood Pellet |
| Versi/build | ______________________________ |
| Lingkungan | ☐ Development ☐ Staging ☐ Production |
| Tanggal pengujian | ______________________________ |
| Penguji / perwakilan pengguna | ______________________________ |
| Penanggung jawab teknis | ______________________________ |

Dokumen ini adalah lembar uji penerimaan. Kolom **Hasil aktual** dan **Status** diisi oleh penguji saat pelaksanaan; skenario di bawah belum dianggap lulus sebelum dijalankan pada lingkungan target.

## 2. Tujuan dan Ruang Lingkup

Memastikan fungsi utama EMS dapat digunakan oleh operator untuk melihat ringkasan konsumsi, status meter, kualitas daya, histori, dan alarm.

Ruang lingkup:

- Dashboard Overview
- Inventaris dan status power meter
- Tampilan real-time
- Kualitas daya
- Histori dan ekspor CSV
- Alarm dan acknowledge
- API, MQTT, serta alur akuisisi
- Penanganan meter offline dan mode demo

## 3. Prasyarat dan Data Uji

Sebelum UAT:

1. Jalankan database, MQTT broker, backend, acquisition worker, dan frontend sesuai [README proyek](../README.md).
2. Pastikan API dapat diakses melalui `/health` dan frontend dapat membuka halaman utama.
3. Catat mode akuisisi: ☐ Simulator ☐ Modbus TCP ke meter riil.
4. Untuk pengujian perangkat riil, pastikan alamat IP, port, slave ID, model, koneksi gateway/jaringan, dan profil register sudah diverifikasi. Jangan menganggap data simulasi sebagai pembacaan meter riil.
5. Siapkan minimal satu periode histori dan satu alarm untuk diuji. Jika menggunakan data seed, catat bahwa data tersebut adalah data demo.
6. Gunakan akun/lingkungan yang disetujui. Jangan menjalankan seed histori demo pada database produksi.

Inventaris seed yang diharapkan: **18 meter, 5 merek, 9 lokasi**. Jumlah tersebut adalah target data konfigurasi awal dan harus dicocokkan dengan inventaris aktual pada lingkungan yang diuji.

## 4. Kriteria Status

- **Lulus**: hasil aktual sesuai seluruh hasil yang diharapkan.
- **Gagal**: hasil aktual tidak sesuai; catat bukti dan buat tiket tindak lanjut.
- **Blocked**: pengujian tidak dapat dijalankan karena prasyarat atau akses belum tersedia.
- **N/A**: skenario tidak relevan untuk lingkungan uji; sertakan alasan.

## 5. Skenario UAT

| ID | Area / skenario | Langkah uji | Hasil yang diharapkan | Hasil aktual / bukti | Status |
|---|---|---|---|---|---|
| UAT-01 | Akses aplikasi | Buka URL frontend pada browser desktop. | Halaman terbuka tanpa error fatal; navigasi menu tersedia. |  |  |
| UAT-02 | Navigasi menu | Buka Overview, Real-time, History, Power Quality, Devices, dan Alarms melalui menu. | Setiap menu membuka halaman yang sesuai dan judul halaman tampil benar. |  |  |
| UAT-03 | Navigasi mobile | Buka aplikasi pada viewport ponsel; buka dan tutup menu navigasi, lalu pilih halaman. | Menu mobile dapat dibuka/ditutup; halaman terpilih terbuka dan menu menutup. |  |  |
| UAT-04 | Ringkasan Overview | Buka Overview dan periksa KPI serta grafik konsumsi. | Ringkasan daya, energi, status perangkat, profil konsumsi, dan distribusi beban ditampilkan; unit nilai terbaca. |  |  |
| UAT-05 | Rekonsiliasi inventaris | Buka Devices dan bandingkan kode/nama meter, merek, model, lokasi, dan status dengan inventaris yang disetujui. | Tidak ada meter yang hilang/duplikat; jumlah, merek, serta lokasi sesuai inventaris aktual. Jika menggunakan seed standar: target 18/5/9. |  |  |
| UAT-06 | Ringkasan per lokasi | Buka Devices dan Real-time; periksa pengelompokan meter per lokasi. | Setiap meter berada pada lokasi yang benar; jumlah meter pada tiap lokasi cocok dengan inventaris. |  |  |
| UAT-07 | Pembacaan real-time - simulator | Pastikan mode simulator aktif, lalu buka Real-time dan amati beberapa siklus polling. | Data simulasi ditandai sebagai demo; nilai dan status diperbarui tanpa dianggap sebagai data perangkat riil. |  |  |
| UAT-08 | Pembacaan real-time - meter riil | Aktifkan mode Modbus pada lingkungan uji; hubungkan meter yang sudah dikonfigurasi, lalu bandingkan nilai EMS dengan tampilan meter pada waktu yang sama. | Meter terhubung dan nilai parameter yang didukung sesuai toleransi yang disepakati; status koneksi ditampilkan benar. Catat meter, waktu, nilai, dan toleransi. |  |  |
| UAT-09 | Meter offline | Putuskan koneksi satu meter uji secara terkendali atau gunakan meter yang tidak dapat dijangkau. | Meter ditandai offline setelah ambang waktu konfigurasi; data lama tidak ditampilkan seolah-olah pembacaan baru; alarm offline muncul sesuai aturan. |  |  |
| UAT-10 | Power Quality | Buka Power Quality dan periksa THD, frekuensi, ambang, serta detail per fasa. | Nilai untuk parameter yang didukung tampil; parameter yang tidak didukung tidak disajikan sebagai angka valid; status ambang sesuai konfigurasi. |  |  |
| UAT-11 | Histori dan filter tanggal | Buka History; pilih rentang tanggal yang memiliki data dan rentang tanpa data. | Grafik, ringkasan, dan tabel mengikuti rentang terpilih; rentang kosong menampilkan pesan tanpa data, bukan error. |  |  |
| UAT-12 | Ekspor histori | Pada History dengan data, pilih Export CSV lalu buka file hasil unduhan. Ulangi saat rentang tidak memiliki data. | File CSV berisi header dan data sesuai rentang; ekspor dinonaktifkan bila tidak ada data. |  |  |
| UAT-13 | Daftar alarm | Buka Alarms pada kondisi terdapat alarm. | Alarm menampilkan pesan, meter terkait, waktu, tingkat keparahan, dan status acknowledge. |  |  |
| UAT-14 | Acknowledge alarm | Pilih acknowledge pada satu alarm yang belum di-ack, lalu muat ulang atau periksa kembali daftar. | Status alarm berubah menjadi acknowledged dan tetap tersimpan pada backend. |  |  |
| UAT-15 | Konektivitas API | Periksa `GET /health`, `GET /api/devices`, `GET /api/summary/today`, `GET /api/alarms`, dan `GET /api/readings`. | Endpoint mengembalikan respons sesuai kontrak; data API konsisten dengan tampilan frontend. |  |  |
| UAT-16 | Validasi parameter histori | Panggil `GET /api/readings` dengan bucket valid dan bucket tidak valid. | Bucket valid menghasilkan data; input tidak valid menghasilkan respons 400 yang dapat dipahami, bukan kegagalan server. |  |  |
| UAT-17 | Alur MQTT ke dashboard | Pada mode akuisisi yang dipilih, amati publish telemetry, ingest backend, dan tampilan data pada dashboard. | Telemetry meter dikenali, tersimpan, dan tampil; status online/offline diperbarui. Tidak ada data demo yang disalahartikan sebagai telemetry riil. |  |  |
| UAT-18 | Pemulihan koneksi | Pulihkan koneksi meter/broker setelah gangguan terkendali. | Worker menyambung kembali sesuai mekanisme retry; pembacaan baru kembali masuk dan status pulih. |  |  |
| UAT-19 | Tampilan demo / backend tidak tersedia | Pada lingkungan non-produksi, hentikan backend atau gunakan lingkungan tanpa data; buka Overview dan Real-time. | Aplikasi menampilkan pemberitahuan demo/error dengan jelas; tidak menyatakan pembacaan simulasi sebagai data riil. Pulihkan layanan setelah pengujian. |  |  |
| UAT-21 | Login dan logout | Buka dashboard tanpa login; login dengan akun valid; klik Logout. | Tanpa login diarahkan ke halaman Login. Login valid membuka halaman tujuan. Password salah menampilkan "Username atau password salah". Logout kembali ke halaman Login. |  |  |
| UAT-22 | Pembatasan percobaan login | Masukkan password salah 6 kali berturut-turut untuk satu username. | Percobaan ke-6 ditolak dengan pesan "Terlalu banyak percobaan login"; tercatat di Audit Log sebagai "Login gagal". |  |  |
| UAT-23 | Hak akses viewer | Login sebagai viewer; periksa menu, tombol Acknowledge alarm, dan buka `/admin/users` langsung. | Menu Admin tidak tampil, tombol Acknowledge tidak ada, halaman admin menampilkan "Akses ditolak". |  |  |
| UAT-24 | Kelola akun | Sebagai admin: buat akun viewer, ubah nama/role, reset password, nonaktifkan akun, lalu hapus akun (ketik ulang username untuk konfirmasi). | Akun baru bisa login. Setelah reset password/nonaktif/hapus, sesi akun tersebut berakhir. Akun yang dihapus hilang dari daftar, tidak bisa login, dan riwayatnya tetap ada di Audit Log. Admin tidak bisa menonaktifkan, menurunkan role, atau menghapus akunnya sendiri. |  |  |
| UAT-25 | Tambah device | Sebagai admin buka Kelola Device; tambah device dengan alamat Modbus yang sudah dipakai, lalu dengan alamat yang benar. | Alamat bentrok ditolak dengan nama device pemakainya. Device baru tersimpan, tampil di dashboard, dan mulai dibaca akuisisi <= 60 detik. |  |  |
| UAT-26 | Nonaktifkan device | Nonaktifkan satu device lalu aktifkan kembali. | Device hilang dari dashboard dan alarm aktifnya ditutup; riwayat di History tetap ada. Setelah diaktifkan, data kembali masuk. Semua aksi tercatat di Audit Log. |  |  |
| UAT-20 | Pemeriksaan total sistem | Bandingkan total daya/energi Overview dengan meter ber-role `incoming` pada waktu/rentang yang sama. | Total hanya menjumlahkan meter incoming; meter outcoming/distribution tidak terhitung ganda. Selisih yang ditemukan dicatat dan disetujui. |  |  |

## 6. Catatan Pengujian dan Temuan

| No. | ID UAT | Temuan / langkah reproduksi | Dampak | Referensi tiket / bukti | PIC | Target penyelesaian |
|---|---|---|---|---|---|---|
| 1 |  |  |  |  |  |  |
| 2 |  |  |  |  |  |  |
| 3 |  |  |  |  |  |  |

## 7. Ringkasan dan Persetujuan

| Ringkasan | Jumlah |
|---|---:|
| Total skenario | 26 |
| Lulus |  |
| Gagal |  |
| Blocked |  |
| N/A |  |

**Kriteria penerimaan yang disarankan:** seluruh skenario kritis yang relevan lulus, tidak ada temuan blocker/high yang belum disetujui, rekonsiliasi inventaris dan data meter disetujui, serta skenario meter riil lulus sebelum sistem dipakai untuk pemantauan operasional.

| Peran | Nama | Keputusan / catatan | Tanggal | Tanda tangan |
|---|---|---|---|---|
| Perwakilan pengguna / operator |  | ☐ Diterima ☐ Diterima dengan catatan ☐ Ditolak |  |  |
| Penanggung jawab proyek |  | ☐ Diterima ☐ Diterima dengan catatan ☐ Ditolak |  |  |
| Penanggung jawab teknis |  | ☐ Diterima ☐ Diterima dengan catatan ☐ Ditolak |  |  |
