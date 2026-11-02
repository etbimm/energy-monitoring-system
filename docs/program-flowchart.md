# Flowchart Program Utama EMS

Diagram ini menggambarkan alur runtime utama sistem berdasarkan implementasi
acquisition worker, backend API, database/MQTT, dan frontend. Acquisition worker
dan API berjalan sebagai proses terpisah.

```mermaid
flowchart TD
    Start([Mulai: docker compose up]) --> Infra[Mulai PostgreSQL / TimescaleDB dan Mosquitto]
    Infra --> ApiStart[FastAPI mulai]
    Infra --> AcqStart[Acquisition worker mulai]
    Infra --> WebStart[Frontend Next.js mulai terpisah]

    subgraph Acquisition["Acquisition worker - backend/app/acquisition"]
        AcqStart --> LoadDevices[Ambil daftar meter aktif dari database]
        LoadDevices --> LoadOK{Database tersedia?}
        LoadOK -- Tidak --> WaitDB[Tunggu 5 detik lalu coba lagi]
        WaitDB --> LoadDevices
        LoadOK -- Ya --> ConnectMQTT[Hubungkan ke MQTT broker]
        ConnectMQTT --> MQTTConnected{Broker terhubung?}
        MQTTConnected -- Tidak --> RetryMQTT[Tunggu 5 detik lalu coba lagi]
        RetryMQTT --> ConnectMQTT
        MQTTConnected -- Ya --> RefreshDevices[Muat ulang daftar meter aktif]
        RefreshDevices --> SelectMode{Mode akuisisi?}
        SelectMode -- simulator --> Simulate[Buat telemetry simulasi]
        SelectMode -- modbus --> ReadModbus[Baca register meter melalui Modbus TCP]
        ReadModbus --> Decode[Decode register sesuai profil model<br/>skala, tipe data, word order]
        Decode --> Normalize[Normalisasi ke payload telemetry]
        Simulate --> HasData{Payload tersedia?}
        Normalize --> HasData
        HasData -- Ya --> PublishTelemetry[Publish telemetry QoS 1]
        HasData -- Tidak --> PublishOffline[Publish status offline]
        PublishTelemetry --> PublishOnline[Publish status online]
        PublishOffline --> NextMeter
        PublishOnline --> NextMeter{Masih ada meter?}
        NextMeter -- Ya --> SelectMode
        NextMeter -- Tidak --> WaitPoll[Tunggu POLL_INTERVAL<br/>default 5 detik]
        WaitPoll --> RefreshDevices
        ReadModbus -. error .-> PublishFailure[Catat kegagalan dan publish status offline]
        PublishFailure --> NextMeter
    end

    subgraph Backend["Backend API - FastAPI"]
        ApiStart --> StartTasks[Mulai MQTT subscriber dan offline watcher]
        StartTasks --> Subscribe[Subscribe ems/meter/+/telemetry]
        Subscribe --> Receive[Terima payload telemetry MQTT]
        Receive --> ValidJSON{Payload JSON valid?}
        ValidJSON -- Tidak --> Ignore[Catat warning dan abaikan payload]
        Ignore --> Receive
        ValidJSON -- Ya --> Ingest[Validasi dan proses telemetry]
        Ingest --> Derive[Hitung nilai turunan<br/>misalnya PF dan kVAh]
        Derive --> Save[Update status meter dan simpan pembacaan<br/>ke PostgreSQL / TimescaleDB]
        Save --> Broadcast[Broadcast event telemetry melalui WebSocket]
        Broadcast --> Receive
        StartTasks --> Watcher[Periksa last-seen meter setiap 15 detik]
        Watcher --> OfflineCheck{Meter melewati ambang offline?}
        OfflineCheck -- Ya --> CreateAlarm[Buat atau perbarui alarm offline]
        OfflineCheck -- Tidak --> Watcher
        CreateAlarm --> Watcher
        ApiStart --> REST[Layani endpoint REST<br/>devices, summary, readings, alarms]
        REST --> DBRead[Baca data dan agregasi dari database]
        DBRead --> REST
        REST --> Ack{Permintaan acknowledge alarm?}
        Ack -- Ya --> UpdateAlarm[Simpan status acknowledge]
        UpdateAlarm --> REST
    end

    subgraph Frontend["Frontend - Next.js"]
        WebStart --> OpenPage[Pengguna membuka dashboard]
        OpenPage --> FetchREST[Ambil devices dan summary melalui REST]
        FetchREST --> DataAvailable{Backend memiliki data?}
        DataAvailable -- Ya --> ShowLive[Tampilkan data backend]
        DataAvailable -- Tidak / gagal --> ShowDemo[Tampilkan fixture demo dan pemberitahuan]
        ShowLive --> SubscribeWS[Hubungkan WebSocket dan polling fallback]
        SubscribeWS --> NewEvent{Event realtime atau interval polling?}
        NewEvent -- Ya --> FetchREST
        ShowLive --> ChoosePage[Pilih halaman dashboard]
        ChoosePage --> Overview[Overview: ringkasan dan grafik 24 jam]
        ChoosePage --> Realtime[Real-time: nilai dan status per meter]
        ChoosePage --> History[History: query rentang waktu dan ekspor CSV]
        ChoosePage --> Quality[Power Quality: THD, frekuensi, dan fase]
        ChoosePage --> Devices[Devices: inventaris per lokasi]
        ChoosePage --> Alarms[Alarms: lihat dan acknowledge alarm]
        History --> Query5m[Request readings dengan bucket 5m]
        Query5m --> DBRead
        Alarms --> Ack
    end

    PublishTelemetry --> Receive
    PublishOnline --> StatusTopic[Publish status meter]
    PublishOffline --> StatusTopic
```

## Ringkasan Alur

1. Acquisition worker mengambil meter aktif dari database, lalu memilih simulator
   atau Modbus berdasarkan `ACQUISITION_MODE`.
2. Pada mode Modbus, worker membaca register melalui Modbus TCP, mendecode
   berdasarkan profil model, lalu menormalisasi data.
3. Worker menerbitkan telemetry dan status ke Mosquitto. Interval bawaan
   acquisition adalah 5 detik.
4. Backend menerima telemetry dari MQTT, memproses dan menyimpan pembacaan,
   kemudian mengirim event realtime melalui WebSocket. REST API melayani data
   dashboard dan histori.
5. Frontend memperbarui data melalui REST berkala dan WebSocket. Bila backend
   tidak tersedia atau belum memiliki data meter, frontend dapat menampilkan
   fixture simulasi lokal dengan pemberitahuan demo.
6. Halaman History meminta bucket 5 menit untuk agregasi data; interval bucket
   berbeda dari interval polling acquisition.

## Titik Masuk Kode

- Acquisition worker: [`backend/app/acquisition/__main__.py`](../backend/app/acquisition/__main__.py)
- Poller Modbus TCP: [`backend/app/acquisition/poller.py`](../backend/app/acquisition/poller.py)
- Profil dan decoding: [`backend/app/acquisition/profiles.py`](../backend/app/acquisition/profiles.py), [`backend/app/acquisition/decoder.py`](../backend/app/acquisition/decoder.py)
- FastAPI dan lifecycle task: [`backend/app/main.py`](../backend/app/main.py)
- Subscriber MQTT: [`backend/app/services/mqtt.py`](../backend/app/services/mqtt.py)
- Frontend data hook: [`frontend/src/lib/use-ems-data.ts`](../frontend/src/lib/use-ems-data.ts)
- Halaman Overview dan permintaan histori 5 menit: [`frontend/src/app/page.tsx`](../frontend/src/app/page.tsx)

## Flowchart Subrutin

Diagram berikut merinci fungsi-fungsi penting yang dipanggil oleh alur utama.

### 1. Subrutin polling Modbus dan decoding

```mermaid
flowchart TD
    A([Mulai poll_device]) --> B[Buat AsyncModbusTcpClient<br/>host, port, timeout]
    B --> C[Hubungkan ke meter / gateway]
    C --> D{Koneksi berhasil?}
    D -- Tidak --> E[Angkat ConnectionError]
    D -- Ya --> F[Ambil register_blocks dari profil model]
    F --> G{Masih ada blok register?}
    G -- Ya --> H{Function code profil}
    H -- FC03 --> I[Baca holding registers]
    H -- FC04 --> J[Baca input registers]
    I --> K{Respons Modbus error?}
    J --> K
    K -- Ya --> L[Angkat ModbusException]
    K -- Tidak --> M[Simpan alamat awal dan words]
    M --> G
    G -- Tidak --> N[Decode tiap blok sesuai tipe data,<br/>skala, dan word order]
    N --> O[Gabungkan hasil per key]
    O --> P[Normalisasi nilai menjadi telemetry]
    P --> Q[Kembalikan payload telemetry]
    E --> R[finally: tutup client]
    L --> R
    Q --> R
```

### 2. Subrutin normalisasi telemetry

```mermaid
flowchart TD
    A([Mulai to_telemetry]) --> B[Terima device_code,<br/>hasil decode, capabilities]
    B --> C[Hitung rata-rata tegangan<br/>dari fase yang tersedia]
    C --> D[Hitung rata-rata arus<br/>dari fase yang tersedia]
    D --> E[Periksa capabilities THD dan unbalance]
    E --> F[Isi parameter opsional yang didukung;<br/>parameter lain menjadi null]
    F --> G[Bentuk objek readings per fase L1/L2/L3]
    G --> H[Tambahkan timestamp UTC]
    H --> I[Kembalikan payload telemetry]
```

### 3. Subrutin ingest MQTT hingga penyimpanan

```mermaid
flowchart TD
    A([Pesan MQTT diterima]) --> B[Decode payload sebagai JSON]
    B --> C{JSON valid?}
    C -- Tidak --> D[Catat warning]
    D --> Z([Abaikan pesan])
    C -- Ya --> E[Panggil ingest_telemetry]
    E --> F[Hitung nilai turunan PF dan kVAh]
    F --> G{device_code tersedia?}
    G -- Tidak --> H[Kembalikan None]
    H --> Z
    G -- Ya --> I[Cari meter berdasarkan device_code]
    I --> J{Meter terdaftar?}
    J -- Tidak --> H
    J -- Ya --> K[Parse timestamp; gunakan waktu sekarang<br/>jika timestamp tidak disertakan]
    K --> L[Merge pembacaan utama ke tabel readings]
    L --> M[Untuk fase L1/L2/L3 yang ada,<br/>merge ke phase_readings]
    M --> N[Perbarui last_seen_at meter]
    N --> O[Hapus alarm offline yang terbuka]
    O --> P[Evaluasi alarm nilai telemetry]
    P --> Q[Commit transaksi database]
    Q --> R[Bentuk snapshot dan hitung status meter]
    R --> S[Simpan latest pada Hub]
    S --> T[Broadcast telemetry melalui WebSocket]
    T --> U([Selesai])
```

### 4. Subrutin evaluasi dan acknowledge alarm

```mermaid
flowchart TD
    A([Telemetry diterima]) --> B[Evaluasi PF, tegangan, frekuensi,<br/>THD-I, unbalance, dan beban]
    B --> C[Buat daftar kondisi aktif<br/>beserta severity dan pesan]
    C --> D[Ambil alarm terbuka untuk meter]
    D --> E{Jenis alarm aktif sudah terbuka?}
    E -- Ya --> F[Perbarui severity dan pesan]
    E -- Tidak --> G[Buat alarm baru]
    G --> H[Broadcast event alarm baru ke WebSocket]
    F --> I[Periksa alarm terbuka yang tidak aktif]
    H --> I
    I --> J[Tandai cleared alarm non-offline<br/>yang kondisinya sudah pulih]
    J --> K([Kembali ke transaksi ingest])

    L([Pengguna acknowledge alarm]) --> M[Cari alarm berdasarkan ID]
    M --> N{Alarm ditemukan?}
    N -- Tidak --> O[Respons HTTP 404]
    N -- Ya --> P[Simpan acknowledged = true<br/>dan waktu acknowledge]
    P --> Q[Kembalikan alarm yang diperbarui]
```

### 5. Subrutin query histori ber-bucket

```mermaid
flowchart TD
    A([GET /api/readings]) --> B[Validasi bucket:<br/>raw, 1m, 5m, 15m, 1h, atau 1d]
    B --> C{Bucket valid?}
    C -- Tidak --> D[Respons HTTP 400]
    C -- Ya --> E[Tentukan rentang waktu default<br/>bila from/to tidak diberikan]
    E --> F{Bucket raw?}
    F -- Ya --> G[Ambil pembacaan tanpa time_bucket]
    F -- Tidak --> H[Kelompokkan per meter dan bucket waktu]
    H --> I[Rata-ratakan nilai daya dan parameter sesaat]
    I --> J[Ambil nilai energi terakhir per meter di bucket]
    G --> K{Permintaan agregat tanpa device?}
    J --> K
    K -- Ya --> L[Agregasikan hanya role yang diminta;<br/>default incoming]
    K -- Tidak --> M[Gunakan device_code yang dipilih]
    L --> N[Bentuk TimeSeriesPoint]
    M --> N
    N --> O([Kembalikan JSON])
```

### 6. Subrutin pembaruan data frontend

```mermaid
flowchart TD
    A([Halaman dashboard dimuat]) --> B[Panggil GET /api/devices<br/>dan GET /api/summary/today]
    B --> C{Request berhasil dan<br/>data meter tersedia?}
    C -- Tidak --> D[Tampilkan fixture lokal<br/>dan pemberitahuan demo/error]
    C -- Ya --> E[Simpan data backend<br/>dan tandai bukan demo]
    D --> F[Hubungkan WebSocket]
    E --> F
    F --> G{WebSocket terhubung?}
    G -- Tidak --> H[Jadwalkan koneksi ulang<br/>setelah 3 detik]
    H --> F
    G -- Ya --> I[Tunggu event telemetry/snapshot<br/>atau polling 15 detik]
    I --> J{Event valid?}
    J -- Tidak --> K[Tampilkan pesan kesalahan]
    J -- Ya --> L[Batasi refresh event<br/>maksimal sekali per detik]
    L --> B
```

## Referensi Subrutin

- Modbus polling: [`backend/app/acquisition/poller.py`](../backend/app/acquisition/poller.py)
- Decode register: [`backend/app/acquisition/decoder.py`](../backend/app/acquisition/decoder.py)
- Normalisasi telemetry: [`backend/app/acquisition/normalize.py`](../backend/app/acquisition/normalize.py)
- Ingest telemetry: [`backend/app/services/ingest.py`](../backend/app/services/ingest.py)
- Perhitungan nilai turunan: [`backend/app/services/derive.py`](../backend/app/services/derive.py)
- Evaluasi alarm: [`backend/app/services/alarms.py`](../backend/app/services/alarms.py)
- Query histori dan inventaris: [`backend/app/services/queries.py`](../backend/app/services/queries.py)
- Hub WebSocket: [`backend/app/services/realtime.py`](../backend/app/services/realtime.py)
- Pembaruan data frontend: [`frontend/src/lib/use-ems-data.ts`](../frontend/src/lib/use-ems-data.ts)
