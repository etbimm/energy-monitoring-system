# Flowchart Program Utama EMS

> Versi flowchart dengan simbol standar laporan (terminator, proses, keputusan,
> input/output, subrutin, penyimpanan data, konektor) tersedia di
> [`flowchart/`](./flowchart/index.html): SVG, PNG, dan draw.io multi-halaman.
> Buat ulang dengan `py scripts/generate_flowcharts.py`.

Versi draw.io multi-halaman yang dapat diedit tersedia di
[`program-flowcharts.drawio`](./program-flowcharts.drawio) dan
[`flowchart/flowchart-ems.drawio`](./flowchart/flowchart-ems.drawio). Keduanya
dibuat oleh generator yang sama; diagram satu halaman, SVG, PNG, dan pratinjau
HTML juga disimpan di [`flowchart/`](./flowchart/).

Diagram ini menggambarkan alur runtime utama sistem berdasarkan implementasi
acquisition worker, backend API, database/MQTT, dan frontend. Acquisition worker
dan API berjalan sebagai proses terpisah.

```mermaid
flowchart TD
    Start([docker compose up: DB, MQTT, backend, acquisition]) --> ApiStart[FastAPI mulai]
    Start --> AcqStart[Acquisition worker mulai]
    WebStart[Frontend Next.js dijalankan terpisah] --> Login[Pengguna login]

    subgraph Acquisition["Acquisition worker - proses terpisah"]
        AcqStart --> LoadDevices[Muat meter aktif dan counter terakhir dari DB]
        LoadDevices --> LoadOK{Database tersedia?}
        LoadOK -- Tidak --> WaitDB[Laporkan error, tunggu 5 detik]
        WaitDB --> LoadDevices
        LoadOK -- Ya --> ConnectMQTT[Hubungkan ke MQTT]
        ConnectMQTT --> MQTTConnected{Broker terhubung?}
        MQTTConnected -- Tidak --> RetryMQTT[Laporkan error dan retry backoff]
        RetryMQTT --> ConnectMQTT
        MQTTConnected -- Ya --> RefreshDevices[Muat ulang meter setiap 60 detik]
        RefreshDevices --> GroupGateway[Kelompokkan per gateway]
        GroupGateway --> PollGateway[Poll gateway paralel;<br/>meter di gateway yang sama berurutan]
        PollGateway --> SelectMode{Mode akuisisi?}
        SelectMode -- simulator --> Simulate[Buat telemetry simulasi]
        SelectMode -- modbus --> ReadModbus[Baca Modbus TCP dengan profil model]
        ReadModbus --> Supported{Profil register tersedia?}
        Supported -- Tidak --> PublishOffline[Publish status offline]
        Supported -- Ya --> Normalize[Decode dan normalisasi telemetry]
        Simulate --> HasData{Payload tersedia?}
        Normalize --> HasData
        HasData -- Ya --> PublishTelemetry[Publish telemetry QoS 1]
        HasData -- Tidak --> PublishOffline
        PublishTelemetry --> PublishOnline[Publish status online]
        PublishOffline --> NextMeter{Masih ada meter?}
        PublishOnline --> NextMeter
        NextMeter -- Ya --> SelectMode
        NextMeter -- Tidak --> WaitPoll[Tunggu hingga deadline POLL_INTERVAL<br/>(default 5 detik; siklus terlambat dilewati)]
        WaitPoll --> RefreshDevices
        ReadModbus -. error baca .-> PublishOffline
        PublishTelemetry -.-> BrokerTelemetry
        PublishOnline -.-> BrokerStatus
        PublishOffline -.-> BrokerStatus
    end

    subgraph Backend["Backend API - FastAPI"]
        ApiStart --> StartTasks[Mulai REST/WS, MQTT subscriber,<br/>offline watcher dan ambang alarm]
        StartTasks --> Subscribe[Subscribe ems/meter/+/telemetry]
        Subscribe --> Receive[Terima payload telemetry MQTT]
        Receive --> ValidJSON{JSON valid?}
        ValidJSON -- Tidak --> Ignore[Catat/laporkan payload invalid]
        Ignore --> Receive
        ValidJSON -- Ya --> ActiveDevice{Device terdaftar dan aktif?}
        ActiveDevice -- Tidak --> Skip[Hitung sebagai pesan diabaikan]
        Skip --> Receive
        ActiveDevice -- Ya --> Derive[Hitung PF dan integrasikan kVAh]
        Derive --> Save[INSERT readings dan phase_readings;<br/>duplikat diabaikan]
        Save --> UpdateSeen[Perbarui last_seen_at;<br/>hapus alarm offline terbuka]
        UpdateSeen --> EvalAlarm[Evaluasi alarm telemetry<br/>(delay dan hysteresis)]
        EvalAlarm --> Commit[Commit transaksi]
        Commit --> Notify[Kirim notifikasi kritis/pulih setelah commit]
        Notify --> Broadcast[Simpan snapshot dan broadcast telemetry/alarm via WS]
        Broadcast --> Receive
        StartTasks --> Watcher[Tunggu 15 detik; periksa meter aktif]
        Watcher --> OfflineCheck{Tanpa last_seen atau melewati ambang?}
        OfflineCheck -- Ya --> CreateAlarm[Buat/perbarui alarm offline<br/>(bawaan warning >30s, critical >180s)]
        OfflineCheck -- Tidak --> Watcher
        CreateAlarm --> Watcher
        ApiStart --> REST[Layani REST; data monitoring perlu login]
        REST --> DBRead[Baca readings / aggregate / alarm dari DB]
        DBRead --> REST
        REST --> Ack{Admin acknowledge alarm?}
        Ack -- Ya --> UpdateAlarm[Simpan acknowledge dan audit log]
        UpdateAlarm --> REST
    end

    BrokerTelemetry[MQTT telemetry topic] --> Receive
    BrokerStatus[MQTT status topic]

    subgraph Frontend["Frontend - Next.js"]
        Login --> FetchREST[Ambil devices dan summary via REST]
        FetchREST --> DataAvailable{Data backend tersedia?}
        DataAvailable -- Ya --> ShowLive[Tampilkan data backend]
        DataAvailable -- Tidak --> DemoMode{NEXT_PUBLIC_DEMO_MODE aktif?}
        DemoMode -- Ya --> ShowDemo[Tampilkan fixture dan tanda Mode demo]
        DemoMode -- Tidak --> ShowError[Tampilkan data kosong dan pesan error]
        ShowLive --> SubscribeWS[Hubungkan WebSocket /ws dengan sesi login]
        ShowDemo --> SubscribeWS
        ShowError --> SubscribeWS
        SubscribeWS --> NewEvent{Pesan WebSocket?}
        NewEvent -- telemetry/snapshot --> Queue[Antrekan per meter;<br/>terapkan paling banyak sekali/detik]
        Queue --> Unknown{Meter baru?}
        Unknown -- Ya --> RefreshUnknown[Sinkron REST dibatasi 10 detik]
        Unknown -- Tidak --> WaitEvent[Tunggu event berikutnya]
        RefreshUnknown --> WaitEvent
        NewEvent -- alarm --> RefreshAlarm[Segarkan data via REST]
        RefreshAlarm --> WaitEvent
        NewEvent -- terputus --> RetryWS[Tunggu 3 detik lalu reconnect]
        RetryWS --> SubscribeWS
        WaitEvent --> FullSync{Interval sinkron 60 detik?}
        FullSync -- Ya --> FetchREST
        FullSync -- Tidak --> NewEvent
        ShowLive --> Pages[Pilih Overview, Real-time, History,<br/>Power Quality, Devices, atau Alarms]
        Pages --> HistoryQuery[History: readings/energy;<br/>default bucket 5m]
        HistoryQuery --> DBRead
    end
```

## Ringkasan Alur

1. Acquisition worker terpisah membaca konfigurasi meter aktif dari PostgreSQL,
   memuat ulang daftar tiap 60 detik, dan mem-poll pada interval bawaan 5 detik.
   Gateway berbeda dipoll paralel; meter di gateway yang sama dibaca berurutan.
2. Pada mode `modbus`, worker membaca Modbus TCP dan mendecode profil model.
   Pada mode `simulator`, telemetry dibuat tanpa hardware. Worker menerbitkan
   telemetry dan status terpisah; backend hanya subscribe topic telemetry.
3. Backend menerima telemetry, mengabaikan device tidak dikenal/nonaktif,
   menghitung PF/kVAh, menyimpan data secara idempoten, memperbarui status
   online dan alarm, lalu menyiarkan WebSocket. Kegagalan MQTT memakai retry
   backoff.
4. Offline watcher backend memeriksa meter aktif tiap 15 detik. Ambang bawaan
   adalah >30 detik untuk warning dan >180 detik untuk critical; device tanpa
   `last_seen_at` langsung critical. Ambang dapat dikonfigurasi.
5. Halaman monitoring memerlukan login. WebSocket reconnect setelah 3 detik;
   telemetry diterapkan tiap detik, alarm memicu sinkron REST, sinkron penuh
   berjalan tiap 60 detik, dan meter baru memicu sinkron terbatas tiap 10 detik.
   Fixture hanya digunakan bila `NEXT_PUBLIC_DEMO_MODE=true`; selain itu UI
   menampilkan data kosong dengan pesan error.
6. History menggunakan default bucket 5 menit. Query raw dibatasi 7 hari dan
   setiap respons time series maksimal 20.000 titik.

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
    A([Mulai pembacaan meter]) --> B[Gunakan koneksi Modbus TCP gateway<br/>persisten pada poller]
    B --> C{Gateway terhubung?}
    C -- Tidak --> D[Buka koneksi ke host:port<br/>timeout konfigurasi]
    D --> E{Koneksi berhasil?}
    E -- Tidak --> F[Angkat error ke poller]
    E -- Ya --> G[Ambil register_blocks<br/>dari profil model]
    C -- Ya --> G
    G --> H{Masih ada blok register?}
    H -- Ya --> I{Function code profil}
    I -- FC03 --> J[Baca holding registers]
    I -- FC04 --> K[Baca input registers]
    J --> L{Respons Modbus error?}
    K --> L
    L -- Ya --> M[Angkat ModbusException]
    L -- Tidak --> N[Simpan alamat awal dan words]
    N --> H
    H -- Tidak --> O[Decode tipe data, skala,<br/>dan word order per register]
    O --> P[Gabungkan hasil dan normalisasi telemetry]
    P --> Q[Kembalikan payload ke poller]
    F --> R([Poller menandai offline;<br/>reconnect bila koneksi gateway putus])
    M --> R
    Q --> S([Koneksi gateway dipakai ulang])
```

### 2. Subrutin normalisasi telemetry

```mermaid
flowchart TD
    A([Mulai to_telemetry]) --> B[Terima device_code,<br/>hasil decode, capabilities]
    B --> C[Hitung rata-rata tegangan<br/>dari fase yang tersedia]
    C --> D[Hitung rata-rata arus<br/>dari fase yang tersedia]
    D --> E[Periksa capabilities THD dan unbalance]
    E --> F[Isi parameter opsional yang didukung;<br/>parameter lain menjadi null]
    F --> G[Gabungkan energi impor T1/T2<br/>bila register tersedia]
    G --> H[Bentuk objek readings per fase L1/L2/L3]
    H --> I[Tambahkan timestamp UTC]
    I --> J[Kembalikan payload telemetry]
```

### 3. Subrutin ingest MQTT hingga penyimpanan

```mermaid
flowchart TD
    A([Pesan MQTT diterima]) --> B[Decode payload sebagai JSON]
    B --> C{JSON valid?}
    C -- Tidak --> D[Laporkan payload invalid]
    D --> Z([Abaikan pesan])
    C -- Ya --> E[Panggil ingest_telemetry]
    E --> G{device_code tersedia?}
    G -- Tidak --> H[Kembalikan None]
    H --> Z
    G -- Ya --> I[Cari meter berdasarkan device_code]
    I --> J{Meter terdaftar dan aktif?}
    J -- Tidak --> H
    J -- Ya --> K[Parse timestamp; tanpa nilai gunakan<br/>waktu sekarang UTC]
    K --> F[Ambil pembacaan sebelumnya;<br/>hitung PF dan integrasikan kVAh]
    F --> L[INSERT readings<br/>ON CONFLICT DO NOTHING]
    L --> M[INSERT phase_readings L1/L2/L3<br/>bila tersedia]
    M --> N[Perbarui last_seen_at meter]
    N --> O[Hapus alarm offline yang terbuka]
    O --> P[Evaluasi alarm nilai telemetry]
    P --> Q[Commit transaksi database]
    Q --> R[Kirim notifikasi alarm kritis/pulih]
    R --> S[Bentuk snapshot dan hitung status meter]
    S --> T[Simpan latest pada Hub]
    T --> U[Broadcast telemetry melalui WebSocket]
    U --> V([Selesai])
```

### 4. Subrutin evaluasi dan acknowledge alarm

```mermaid
flowchart TD
    A([Telemetry diterima]) --> B[Ambil ambang dari cache DB;<br/>evaluasi PF, tegangan, frekuensi, THD-I, unbalance, beban]
    B --> C[Bandingkan kondisi aktif<br/>dengan alarm terbuka per meter]
    C --> D{Alarm sudah terbuka?}
    D -- Ya --> E{Masih abnormal<br/>dengan deadband?}
    E -- Ya --> F[Perbarui severity dan pesan;<br/>batalkan timer pemulihan]
    E -- Tidak --> G{Normal selama<br/>off-delay?}
    G -- Ya --> H[Tandai alarm cleared]
    G -- Tidak --> I[Pertahankan alarm;<br/>lanjutkan timer pemulihan]
    D -- Tidak --> J{Abnormal selama<br/>on-delay?}
    J -- Ya --> K[Buat alarm baru]
    J -- Tidak --> L[Batalkan timer pending]
    K --> M[Broadcast event alarm baru via WS]
    F --> N[Commit transaksi ingest]
    H --> N
    I --> N
    L --> N
    M --> N
    N --> O{Alarm kritis baru<br/>atau pulih/turun?}
    O -- Ya --> P[Kirim notifikasi Telegram<br/>setelah commit]
    O -- Tidak --> Q([Kembali dari ingest])
    P --> Q

    R([Admin acknowledge alarm]) --> S[Validasi role Admin;<br/>cari alarm berdasarkan ID]
    S --> T{Alarm ditemukan?}
    T -- Tidak --> U[Respons HTTP 404]
    T -- Ya --> V[Simpan acknowledged dan waktu;<br/>catat audit log]
    V --> W[Kembalikan alarm yang diperbarui]
```

### 5. Subrutin query histori ber-bucket

```mermaid
flowchart TD
    A([GET /api/readings atau /api/energy]) --> B[Validasi rentang dan bucket:<br/>raw, 1m, 5m, 15m, 1h, atau 1d]
    B --> C{Bucket valid?}
    C -- Tidak --> D[Respons HTTP 400]
    C -- Ya --> E[Tentukan rentang waktu default<br/>bila from/to tidak diberikan]
    E --> F{Bucket raw?}
    F -- Ya --> G{Device tunggal?}
    G -- Ya --> H[Baca readings mentah]
    G -- Tidak --> I[Gunakan bucket 1 menit]
    F -- Tidak --> I
    I --> J[Kelompokkan per device dan bucket;<br/>AVG metrik, last energi]
    J --> K
    H --> K
    K -- Ya --> L[Agregasikan hanya role yang diminta;<br/>default incoming]
    K -- Tidak --> M[Gunakan device_code yang dipilih]
    L --> N[Bentuk TimeSeriesPoint]
    M --> N
    N --> O[Kembalikan JSON;<br/>raw max 7 hari, total max 20.000 titik]
    O --> P([Selesai])

    A --> Q[GET /api/energy: delta per device]
    Q --> R{Rentang ≥7 hari<br/>dan selaras tengah malam WIB?}
    R -- Tidak --> S[Gunakan readings_1min]
    R -- Ya --> T[Gunakan daily_energy<br/>untuk hari lengkap]
    T --> U[Gunakan readings_15min<br/>untuk tepi rentang dan kVAh]
    S --> V[Jumlahkan delta positif per device]
    U --> V
    V --> W([Kembalikan total energi])
```

### 6. Subrutin pembaruan data frontend

```mermaid
flowchart TD
    A([Halaman dashboard dimuat<br/>dengan sesi login]) --> B[Panggil GET /api/devices<br/>dan GET /api/summary/today]
    B --> C{Request berhasil dan<br/>data meter tersedia?}
    C -- Tidak --> D{NEXT_PUBLIC_DEMO_MODE aktif?}
    D -- Ya --> E[Tampilkan fixture lokal<br/>dan tanda Mode demo]
    D -- Tidak --> F[Tampilkan data kosong<br/>dan pesan error]
    C -- Ya --> G[Simpan data backend<br/>dan tandai bukan demo]
    E --> H[Hubungkan WebSocket /ws]
    F --> H
    G --> H
    H --> I{WebSocket terhubung?}
    I -- Tidak --> J[Jadwalkan koneksi ulang<br/>setelah 3 detik]
    J --> H
    I -- Ya --> K{Jenis pesan WebSocket?}
    K -- Telemetry/snapshot --> L[Antrekan per meter;<br/>terapkan paling banyak tiap detik]
    L --> M{Ada meter baru?}
    M -- Ya --> N[Sinkron REST dibatasi<br/>tiap 10 detik]
    M -- Tidak --> O[Tunggu pesan berikutnya]
    N --> O
    K -- Alarm --> P[Segarkan data dengan REST]
    P --> O
    O --> Q{Interval REST penuh 60 detik?}
    Q -- Ya --> B
    Q -- Tidak --> K
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
