# Node-RED

Flow Node-RED untuk parsing data dari power meter.

## Isi Folder

```
node-red/
|- meter-profiles.js       # profil register + skala per model meter (acuan parsing)
|- meter-profiles.test.js  # uji decoder: node meter-profiles.test.js
|- register-map.md         # tabel register versi ringkas untuk lapangan
|- flows.json              # (rencana) flow utama, export dari Node-RED
|- package.json            # (rencana) custom nodes (node-red-contrib-modbus)
`- settings.js             # (rencana) konfigurasi port & auth
```

## Acuan Parsing

| Dokumen | Isi |
|---|---|
| [`register-map.md`](./register-map.md) | Tabel register, skala, dan tipe data per model meter — untuk commissioning di lapangan |
| [`meter-profiles.js`](./meter-profiles.js) | Versi mesin-readable dari tabel di atas, lengkap dengan fungsi `decode()` dan `derive()` |
| [`../docs/parameter-specification.md`](../docs/parameter-specification.md) | Spesifikasi parameter 3 lapis, kontrak payload MQTT, dan skema DB |

## Aturan Saat Parsing

1. **Selalu decode sebelum publish.** Nilai mentah register tidak boleh keluar
   dari Node-RED. Gunakan `decode(profile, words)` dari `meter-profiles.js`.
2. **Skala berbeda per model.** PAC3220 & Elite440 = IEEE754 float; sisanya
   integer berskala (10 / 100 / 1000). Ambil `scale` dari profil, jangan hardcode.
3. **Jangan poll `kVAh` dan `PF`.** Hanya PAC3220 punya register kVAh, dan
   definisi register PF berbeda antar model. Keduanya dihitung di backend.
4. **Parameter opsional nullable.** THD / unbalance yang tidak didukung meter
   dipublish `null`, bukan `0`. `0` berarti "sehat".
5. **Energy dipoll 1 menit**, ambil delta. Register energy kumulatif bisa
   overflow 32-bit.

## Uji

```bash
node meter-profiles.test.js
```

Uji mencakup pembacaan register dasar, decode tiap model (termasuk register
yang tidak berurutan), parameter turunan, dan integritas registry
(konsistensi `count` vs tipe data, register tidak bertumpuk, alamat unik).

## Setup Nanti

1. `docker run -d -p 1880:1880 nodered/node-red`
2. Buka http://localhost:1880
3. Install `node-red-contrib-modbus` lewat menu Manage palette
4. Susun flow sesuai `docs/node-red-flow.md`, memakai profil dari
   `meter-profiles.js`

## Catatan

- Port 1880 hanya untuk development. Di production, Node-RED sebaiknya tidak
  di-expose ke jaringan publik.
- 18 power meter memakai 5 model berbeda dengan setting serial berbeda
  (baud / parity / slave id). **Slave ID wajib diubah dari default 1** agar
  tidak bentrok dalam satu segmen RS485.
- Batas segmen RS485: 1.200 m, 32 unit. 5 unit PAC3220 di LVMDP connect
  langsung via Ethernet, bukan lewat converter.
