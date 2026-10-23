# Node-RED Flow

Dokumentasi ini akan diisi setelah perangkat keras (meter + converter) siap.

## Rencana Flow

```
[Modbus Read] -> [Function: parse & scale] -> [Filter: validasi] -> [MQTT Out: ems/#]
      ^                                                                  |
      |                                                                  v
[Modbus Flex Getter / Inject timer]                          [MQTT In -> Backend]
```

## Node yang Dibutuhkan

| Node | Paket | Fungsi |
|---|---|---|
| Modbus Read / Modbus-Flex-Getter | `node-red-contrib-modbus` | baca register dari meter |
| Inject | bawaan | trigger polling sesuai interval |
| Function | bawaan | ubah raw register jadi JSON matang |
| MQTT In/Out | bawaan | bridge ke backend |

## Yang Perlu Dikerjakan

- [ ] Petakan register Modbus tiap tipe meter
- [ ] Tentukan interval polling (rekomendasi mulai 5 detik)
- [ ] Tulis function parsing + scaling (float32, skala, byte order)
- [ ] Validasi data (null, NaN, out of range)
- [ ] Publish ke topic `ems/meter/{code}/telemetry`
- [ ] Tambahkan watchdog / heartbeat untuk deteksi offline

## Catatan Penting

- **Byte order & word order** Modbus sering jadi sumber data salah baca.
  Selalu verifikasi dengan membandingkan nilai UI meter dengan nilai di Node-RED.
- **Polling jangan terlalu cepat.** RS485 Itu lambat (9600 baud ~需要的).
  5 detik per meter sudah lebih dari cukup untuk monitoring.
- **Tangani timeout.** Kalau converter tidak merespons, node harus
  lanjut ke meter berikutnya, bukan menggantung flow.