/**
 * ============================================================================
 *  PROFIL POWER METER  —  acuan parsing Node-RED
 * ============================================================================
 *
 *  Berkas ini adalah SATU-SATUNYA sumber kebenaran untuk:
 *    - alamat register Modbus tiap model meter
 *    - faktor skala / konversi tiap register
 *    - tipe data (int berskala, int16, atau IEEE754 float)
 *    - urutan byte (endianness)
 *    - parameter yang TIDAK tersedia di model tersebut
 *
 *  Semua register di bawah mengikuti konvensi "input register" (FC 04)
 *  dengan alamat 0-based, ARTIFACT Address = 40001 + addr.
 *  WAJIB konfirmasi ulang ke manual alat saat commissioning.
 *
 *  ------------------------------------------------------------------
 *  CARA PAKAI
 *  ------------------------------------------------------------------
 *  1. Salin objek profil yang sesuai ke konfigurasi node Modbus-Flex
 *     pada node-red/flows/meter-polling.json
 *  2. Pakai fungsi `decode()` di bawah untuk mengubah respons mentah
 *     menjadi nilai engineering (satuan SI).
 *  3. JANGAN pernah menyimpan angka mentah ke MQTT/DB. Selalu decode dulu.
 *
 *  ------------------------------------------------------------------
 *  ATURAN SKALA YANG SERING SALAH
 *  ------------------------------------------------------------------
 *  - Register integer bisa berskala 0.1 (contoh: 1186 = 118.6 kW)
 *    ATAU 10 (contoh: 1186 = 11.86 kW). Tidak boleh diasumsikan sama
 *    antar model.
 *  - kWh pada register 32-bit sering PECAH jadi 2x register 16-bit
 *    (high word di register lebih rendah, little-endian).
 *  - PAC3220 dan Elite440 memakai FLOAT IEEE754, TIDAK boleh
 *    diperlakukan sebagai integer.
 *  - Register energy bersifat KUMULATIF dan bisa 32-bit. Polling
 *    tiap detik tidak perlu - cukup 1 menit, lalu delta.
 *
 *  @author  EMS - Java Wood Pellet
 *  @version 1.0.0
 */

// ---------------------------------------------------------------------------
//  Definisi tipe register
// ---------------------------------------------------------------------------

/**
 * @typedef {Object} RegisterDef
 * @property {number}  addr        Alamat input register (0-based)
 * @property {number}  count       Jumlah register yang dibaca (1 atau 2)
 * @property {string}  label       Nama parameter
 * @property {string}  unit        Satuan engineering
 * @property {"uint16"|"int16"|"uint32"|"int32"|"float32"|"float64"} type
 * @property {number}  scale       Pembagi: engineering = raw / scale
 * @property {string}  [note]      Catatan khusus
 */

/**
 * @typedef {Object} MeterProfile
 * @property {string}   model          Nama model
 * @property {string}   brand
 * @property {number}   defaultSlaveId Slave ID Modbus default
 * @property {number}   defaultBaud
 * @property {number}   defaultParity  0=NONE, 1=ODD, 2=EVEN
 * @property {number}   defaultStopBits
 * @property {string}   functionCode  "FC04" input register, "FC03" holding
 * @property {RegisterDef[]} registers
 * @property {string[]}  available     Parameter yang tersedia
 * @property {string[]}  unavailable   Parameter yang TIDAK tersedia
 * @property {string}    [notes]
 */

// ---------------------------------------------------------------------------
//  1. SIEMENS PAC3220  (LVMDP Incoming, 5 unit)
// ---------------------------------------------------------------------------
/**
 * Equipment Manual L1V30425208F_RS-AA_002, 07/2024, bab "Technical data".
 * Data float IEEE754, little-endian, 2 register per nilai.
 * Bawaan 2x Ethernet; RS485 butuh expansion module.
 */
const PAC3220 = {
  model: "SIEMENS PAC3220",
  brand: "Siemens SENTRON 7KM",
  defaultSlaveId: 1,
  defaultBaud: 19200,
  defaultParity: 0,
  defaultStopBits: 1,
  functionCode: "FC04",
  registers: [
    { addr: 800, count: 1, label: "U L1-L2", unit: "V", type: "uint16", scale: 10 },
    { addr: 801, count: 1, label: "U L2-L3", unit: "V", type: "uint16", scale: 10 },
    { addr: 802, count: 1, label: "U L3-L1", unit: "V", type: "uint16", scale: 10 },
    { addr: 805, count: 1, label: "I L1", unit: "A", type: "uint16", scale: 100 },
    { addr: 806, count: 1, label: "I L2", unit: "A", type: "uint16", scale: 100 },
    { addr: 807, count: 1, label: "I L3", unit: "A", type: "uint16", scale: 100 },
    { addr: 850, count: 2, label: "P total", unit: "kW", type: "float32", scale: 1, note: "kW aktif total" },
    { addr: 852, count: 2, label: "Q total", unit: "kVAR", type: "float32", scale: 1 },
    { addr: 854, count: 2, label: "S total", unit: "kVA", type: "float32", scale: 1 },
    { addr: 856, count: 2, label: "PF total", unit: "-", type: "float32", scale: 1 },
    { addr: 860, count: 2, label: "Frekuensi", unit: "Hz", type: "float32", scale: 1 },
    { addr: 870, count: 2, label: "THD I L1", unit: "%", type: "float32", scale: 1 },
    { addr: 872, count: 2, label: "THD I L2", unit: "%", type: "float32", scale: 1 },
    { addr: 874, count: 2, label: "THD I L3", unit: "%", type: "float32", scale: 1 },
    { addr: 876, count: 2, label: "THD U L1", unit: "%", type: "float32", scale: 1 },
    { addr: 878, count: 2, label: "THD U L2", unit: "%", type: "float32", scale: 1 },
    { addr: 880, count: 2, label: "THD U L3", unit: "%", type: "float32", scale: 1 },
    { addr: 884, count: 2, label: "Unbalance U", unit: "%", type: "float32", scale: 1 },
    { addr: 886, count: 2, label: "Unbalance I", unit: "%", type: "float32", scale: 1 },
    { addr: 900, count: 2, label: "Active energy import T1", unit: "kWh", type: "uint32", scale: 100, note: "kumulatif, 2x16bit, little-endian" },
    { addr: 902, count: 2, label: "Reactive energy import T1", unit: "kVARh", type: "uint32", scale: 100 },
    { addr: 904, count: 2, label: "Apparent energy T1", unit: "kVAh", type: "uint32", scale: 100, note: "satu-satunya model dengan kVAh native" },
  ],
  available: ["V", "I", "kW", "kVA", "kVAR", "kWh", "kVAh", "kVARh", "THD-i", "THD-u", "unbalance", "PF", "Hz", "demand"],
  unavailable: [],
  notes:
    "Nilai float IEEE754 little-endian. Register kVAh native ada di model ini saja. " +
    "Pakai expansion module bila butuh RS485; secara bawaan PAC3220 memakai Ethernet.",
};

// ---------------------------------------------------------------------------
//  2. LOVATO DMG510  (LVMDP Outcoming, 3 unit)
// ---------------------------------------------------------------------------
/**
 * Manual instalasi 604 GB I 09 19.
 * Punya analisis harmonik sampai orde 15 (setting P02.12 = THD+HAR).
 * Energy: aktif class 1, reaktif class 2. TIDAK ada kVAh.
 */
const DMG510 = {
  model: "LOVATO DMG510",
  brand: "Lovato Electric",
  defaultSlaveId: 1,
  defaultBaud: 9600,
  defaultParity: 0,
  defaultStopBits: 1,
  functionCode: "FC03",
  registers: [
    { addr: 3000, count: 1, label: "V L1", unit: "V", type: "uint16", scale: 10 },
    { addr: 3001, count: 1, label: "V L2", unit: "V", type: "uint16", scale: 10 },
    { addr: 3002, count: 1, label: "V L3", unit: "V", type: "uint16", scale: 10 },
    { addr: 3003, count: 1, label: "I L1", unit: "A", type: "uint16", scale: 100 },
    { addr: 3004, count: 1, label: "I L2", unit: "A", type: "uint16", scale: 100 },
    { addr: 3005, count: 1, label: "I L3", unit: "A", type: "uint16", scale: 100 },
    { addr: 3006, count: 2, label: "P aktif", unit: "kW", type: "int32", scale: 100 },
    { addr: 3008, count: 2, label: "Q reaktif", unit: "kVAR", type: "int32", scale: 100 },
    { addr: 3010, count: 2, label: "S semu", unit: "kVA", type: "int32", scale: 100 },
    { addr: 3012, count: 1, label: "PF", unit: "-", type: "int16", scale: 1000, note: "bagi 1000" },
    { addr: 3013, count: 1, label: "Frekuensi", unit: "Hz", type: "uint16", scale: 10 },
    { addr: 3100, count: 1, label: "THD I L1", unit: "%", type: "uint16", scale: 10, note: "butuh P02.12 = THD+HAR" },
    { addr: 3101, count: 1, label: "THD U L1", unit: "%", type: "uint16", scale: 10 },
    { addr: 3200, count: 2, label: "Active energy import", unit: "kWh", type: "uint32", scale: 100 },
    { addr: 3202, count: 2, label: "Reactive energy import", unit: "kVARh", type: "uint32", scale: 100 },
  ],
  available: ["V", "I", "kW", "kVA", "kVAR", "kWh", "kVARh", "THD-i", "THD-u", "PF", "Hz", "demand"],
  unavailable: ["kVAh", "unbalance"],
  notes:
    "THD hanya aktif bila P02.12 disetel ke THD+HAR (bukan THD). " +
    "Harmonik sampai orde 15. TIDAK punya register kVAh - hitung di backend dari kVA.",
};

// ---------------------------------------------------------------------------
//  3. CEWE Elite440  (MVMDP, 1 unit)
// ---------------------------------------------------------------------------
/**
 * Datasheet CEWE Elite 440 (7-18/Nov 21).
 * Data float IEEE754 (IEEE 754 compliant, floating point).
 * THD rata-rata untuk tegangan, arus, dan daya sampai orde 31.
 * Load survey 40 hari, 6 parameter, interval 30 menit.
 */
const ELITE440 = {
  model: "CEWE Elite440",
  brand: "CEWE Instrument",
  defaultSlaveId: 1,
  defaultBaud: 9600,
  defaultParity: 0,
  defaultStopBits: 1,
  functionCode: "FC03",
  registers: [
    { addr: 0, count: 2, label: "U L1", unit: "V", type: "float32", scale: 1 },
    { addr: 2, count: 2, label: "U L2", unit: "V", type: "float32", scale: 1 },
    { addr: 4, count: 2, label: "U L3", unit: "V", type: "float32", scale: 1 },
    { addr: 6, count: 2, label: "I L1", unit: "A", type: "float32", scale: 1 },
    { addr: 8, count: 2, label: "I L2", unit: "A", type: "float32", scale: 1 },
    { addr: 10, count: 2, label: "I L3", unit: "A", type: "float32", scale: 1 },
    { addr: 12, count: 2, label: "P aktif", unit: "kW", type: "float32", scale: 1 },
    { addr: 14, count: 2, label: "Q reaktif", unit: "kVAR", type: "float32", scale: 1 },
    { addr: 16, count: 2, label: "S semu", unit: "kVA", type: "float32", scale: 1 },
    { addr: 18, count: 2, label: "PF", unit: "-", type: "float32", scale: 1 },
    { addr: 20, count: 2, label: "Frekuensi", unit: "Hz", type: "float32", scale: 1 },
    { addr: 22, count: 2, label: "THD I L1", unit: "%", type: "float32", scale: 1, note: "rata-rata, s/d orde 31" },
    { addr: 24, count: 2, label: "THD U L1", unit: "%", type: "float32", scale: 1 },
    { addr: 26, count: 2, label: "THD P L1", unit: "%", type: "float32", scale: 1 },
    { addr: 40, count: 2, label: "Active energy import", unit: "kWh", type: "uint32", scale: 1 },
    { addr: 42, count: 2, label: "Reactive energy import", unit: "kVARh", type: "uint32", scale: 1 },
  ],
  available: ["V", "I", "kW", "kVA", "kVAR", "kWh", "kVARh", "THD-i", "THD-u", "PF", "Hz", "demand"],
  unavailable: ["kVAh", "unbalance"],
  notes:
    "Meter multi-line: register dipetakan per baris (L1/L2/L3) via konfigurasi. " +
    "Nilai float IEEE754 - decoder float32, bukan integer.",
};

// ---------------------------------------------------------------------------
//  4. ACREL AMC96  (MCC 1-4, 6 unit)
// ---------------------------------------------------------------------------
/**
 * Datasheet Acrel AMC96L-E4 (seri AMC).
 * Standar: I, U, kW, kvar, kVA, kWh, kvarh, Hz, cosPhi.
 * THDi/THDu + harmonik orde 2-31 HANYA bila opsi /H terpasang.
 * TIDAK punya kVAh.
 */
const AMC96 = {
  model: "ACREL AMC96",
  brand: "Acrel",
  defaultSlaveId: 1,
  defaultBaud: 9600,
  defaultParity: 0,
  defaultStopBits: 1,
  functionCode: "FC03",
  registers: [
    { addr: 0, count: 1, label: "U L1", unit: "V", type: "uint16", scale: 10 },
    { addr: 1, count: 1, label: "U L2", unit: "V", type: "uint16", scale: 10 },
    { addr: 2, count: 1, label: "U L3", unit: "V", type: "uint16", scale: 10 },
    { addr: 3, count: 1, label: "I L1", unit: "A", type: "uint16", scale: 100 },
    { addr: 4, count: 1, label: "I L2", unit: "A", type: "uint16", scale: 100 },
    { addr: 5, count: 1, label: "I L3", unit: "A", type: "uint16", scale: 100 },
    { addr: 6, count: 1, label: "P aktif", unit: "kW", type: "uint16", scale: 10 },
    { addr: 7, count: 1, label: "Q reaktif", unit: "kVAR", type: "uint16", scale: 10 },
    { addr: 8, count: 1, label: "S semu", unit: "kVA", type: "uint16", scale: 10 },
    { addr: 9, count: 1, label: "PF", unit: "-", type: "uint16", scale: 100, note: "bagi 100" },
    { addr: 10, count: 1, label: "Frekuensi", unit: "Hz", type: "uint16", scale: 10 },
    { addr: 11, count: 1, label: "THD I (opsi /H)", unit: "%", type: "uint16", scale: 10, note: "HANYA bila opsi /H terpasang" },
    { addr: 12, count: 1, label: "THD U (opsi /H)", unit: "%", type: "uint16", scale: 10 },
    { addr: 30, count: 2, label: "Active energy import", unit: "kWh", type: "uint32", scale: 100 },
    { addr: 32, count: 2, label: "Reactive energy import", unit: "kVARh", type: "uint32", scale: 100 },
  ],
  available: ["V", "I", "kW", "kVA", "kVAR", "kWh", "kVARh", "THD-i", "THD-u", "PF", "Hz"],
  unavailable: ["kVAh", "unbalance", "demand"],
  notes:
    "Register 11-12 (THD) mengembalikan 0 / error bila opsi /H tidak terpasang. " +
    "Verifikasi fisik unit saat commissioning: ada port /H atau tidak.",
};

// ---------------------------------------------------------------------------
//  5. WEIDMULLER EM220  (MCC Pellet 1-3, 3 unit)
// ---------------------------------------------------------------------------
/**
 * Data sheet EM220-RTU-4DI2DO (BasicLine).
 * Update interval register 1 detik. Class 0.5S active energy, 0.5 reactive.
 * TIDAK ada harmonik / THD. TIDAK ada kVAh.
 * Display: U, I, S, Q, PF, Hz, import/export active & reactive energy, demand.
 */
const EM220 = {
  model: "WEIDMULLER EM220",
  brand: "Weidmuller",
  defaultSlaveId: 1,
  defaultBaud: 9600,
  defaultParity: 0,
  defaultStopBits: 1,
  functionCode: "FC03",
  registers: [
    { addr: 0, count: 1, label: "U L1", unit: "V", type: "uint16", scale: 10 },
    { addr: 1, count: 1, label: "U L2", unit: "V", type: "uint16", scale: 10 },
    { addr: 2, count: 1, label: "U L3", unit: "V", type: "uint16", scale: 10 },
    { addr: 3, count: 1, label: "I L1", unit: "A", type: "uint16", scale: 100 },
    { addr: 4, count: 1, label: "I L2", unit: "A", type: "uint16", scale: 100 },
    { addr: 5, count: 1, label: "I L3", unit: "A", type: "uint16", scale: 100 },
    { addr: 6, count: 2, label: "P aktif", unit: "kW", type: "uint32", scale: 1000 },
    { addr: 8, count: 2, label: "Q reaktif", unit: "kVAR", type: "int32", scale: 1000 },
    { addr: 10, count: 2, label: "S semu", unit: "kVA", type: "uint32", scale: 1000 },
    { addr: 12, count: 1, label: "PF", unit: "-", type: "int16", scale: 1000 },
    { addr: 13, count: 1, label: "Frekuensi", unit: "Hz", type: "uint16", scale: 100 },
    { addr: 20, count: 2, label: "Active energy import", unit: "kWh", type: "uint32", scale: 100 },
    { addr: 22, count: 2, label: "Reactive energy import", unit: "kVARh", type: "uint32", scale: 100 },
    { addr: 24, count: 2, label: "Active energy export", unit: "kWh", type: "uint32", scale: 100 },
    { addr: 26, count: 2, label: "Reactive energy export", unit: "kVARh", type: "uint32", scale: 100 },
  ],
  available: ["V", "I", "kW", "kVA", "kVAR", "kWh", "kVARh", "PF", "Hz", "demand"],
  unavailable: ["kVAh", "THD-i", "THD-u", "unbalance"],
  notes:
    "Meter BasicLine: sengaja tidak punya analisis harmonik. " +
    "Punya import DAN export (4 kuadran) untuk energi aktif & reaktif. " +
    "Update register internal tiap 1 detik - polling lebih cepat dari 5 detik sia-sia.",
};

// ---------------------------------------------------------------------------
//  Registry
// ---------------------------------------------------------------------------

const PROFILES = {
  "SIEMENS PAC3220": PAC3220,
  "LOVATO DMG510": DMG510,
  "CEWE Elite440": ELITE440,
  "ACREL AMC96": AMC96,
  "WEIDMULLER EM220": EM220,
};

/** Mapping deviceId -> model, untuk lookup profil saat polling */
const DEVICE_MODEL = {
  "PM-LVMDP-IN-01": "SIEMENS PAC3220",
  "PM-LVMDP-IN-02": "SIEMENS PAC3220",
  "PM-LVMDP-IN-03": "SIEMENS PAC3220",
  "PM-LVMDP-IN-04": "SIEMENS PAC3220",
  "PM-LVMDP-IN-05": "SIEMENS PAC3220",
  "PM-LVMDP-OUT-01": "LOVATO DMG510",
  "PM-LVMDP-OUT-02": "LOVATO DMG510",
  "PM-LVMDP-OUT-03": "LOVATO DMG510",
  "PM-MVMDP-01": "CEWE Elite440",
  "PM-MCC1-01": "ACREL AMC96",
  "PM-MCC1-02": "ACREL AMC96",
  "PM-MCC2-01": "ACREL AMC96",
  "PM-MCC3-01": "ACREL AMC96",
  "PM-MCC3-02": "ACREL AMC96",
  "PM-MCC4-01": "ACREL AMC96",
  "PM-PEL1-01": "WEIDMULLER EM220",
  "PM-PEL2-01": "WEIDMULLER EM220",
  "PM-PEL3-01": "WEIDMULLER EM220",
};

// ---------------------------------------------------------------------------
//  Decoder
// ---------------------------------------------------------------------------

/**
 * Baca register uint32 dari dua register 16-bit (little-endian).
 * @param {number[]} words  pasangan register [low, high]
 */
function readUint32LE(words) {
  return words[0] + words[1] * 65536;
}

/**
 * Baca register int32 dari dua register 16-bit (little-endian, two's complement).
 */
function readInt32LE(words) {
  const v = readUint32LE(words);
  return v > 0x7fffffff ? v - 0x100000000 : v;
}

/**
 * Baca IEEE754 float32 dari dua register 16-bit (little-endian).
 */
function readFloat32LE(words) {
  const buf = new ArrayBuffer(4);
  const view = new DataView(buf);
  view.setUint16(0, words[0], true);
  view.setUint16(2, words[1], true);
  return view.getFloat32(0, true);
}

/**
 * Ubah register Modbus mentah (array of 16-bit words) menjadi objek
 * parameter engineering.
 *
 * PENTING: alamat register antar-parameter TIDAK selalu berurutan
 * (mis. Elite440 lompat dari addr 26 ke addr 40). Karena itu indeks dihitung
 * dari `addr`, bukan dari kursor berjalan.
 *
 * @param {object} profile  Profil meter (lihat PROFILES)
 * @param {number[]} words   Words hasil baca Modbus
 * @param {number} [baseAddr] Alamat register pertama yang ada di `words`
 *                           (default: alamat register pertama pada profil)
 * @returns {object}  { label: { value, unit } }
 */
function decode(profile, words, baseAddr) {
  const out = {};
  const base = baseAddr ?? profile.registers[0].addr;

  for (const reg of profile.registers) {
    const start = reg.addr - base;
    const slice = words.slice(start, start + reg.count);

    if (slice.length < reg.count) {
      // register tidak ikut terbaca (jarak register > rentang baca)
      continue;
    }

    let raw;
    switch (reg.type) {
      case "uint16":
        raw = slice[0];
        break;
      case "int16":
        raw = slice[0] > 0x7fff ? slice[0] - 0x10000 : slice[0];
        break;
      case "uint32":
        raw = readUint32LE(slice);
        break;
      case "int32":
        raw = readInt32LE(slice);
        break;
      case "float32":
        raw = readFloat32LE(slice);
        break;
      default:
        raw = slice[0];
    }

    out[reg.label] = {
      value: Math.round((raw / reg.scale) * 1000) / 1000,
      unit: reg.unit,
    };
  }

  return out;
}

/**
 * Hitung parameter turunan (L2) dari nilai hasil decode.
 * Semua turunan dihitung di backend, TIDAK dipoll dari meter.
 *
 * @param {object} d  objek hasil decode()
 */
function derive(d) {
  const get = (label) => (d[label] ? d[label].value : null);
  const kW = get("P aktif") ?? get("P total");
  const kVA = get("S semu") ?? get("S total");
  const kVAR = get("Q reaktif") ?? get("Q total");

  const result = {};

  // PF = kW / kVA  (fallback ke register PF bila kVA tidak terbaca)
  const pfReg = get("PF");
  result.powerFactor =
    kW !== null && kVA ? Math.round((kW / kVA) * 1000) / 1000 : pfReg;

  // kVAh = kWh / PF  (ekuivalen dengan integral kVA dt untuk PF konstan)
  const kWh = get("Active energy import") ?? get("Active energy import T1");
  if (kWh !== null && result.powerFactor) {
    result.energyApparent = Math.round((kWh / result.powerFactor) * 100) / 100;
  }

  return result;
}

module.exports = {
  PROFILES,
  DEVICE_MODEL,
  decode,
  derive,
  readUint32LE,
  readInt32LE,
  readFloat32LE,
};
