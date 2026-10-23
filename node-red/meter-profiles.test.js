/**
 * Uji decoder meter-profiles.js
 * Jalankan: node node-red/meter-profiles.test.js
 */
const assert = require("node:assert");
const {
  PROFILES,
  DEVICE_MODEL,
  decode,
  derive,
  readUint32LE,
  readInt32LE,
  readFloat32LE,
} = require("./meter-profiles.js");

let passed = 0;
function check(name, fn) {
  try {
    fn();
    passed++;
    console.log(`  OK   ${name}`);
  } catch (e) {
    console.error(`  FAIL ${name}\n       ${e.message}`);
    process.exitCode = 1;
  }
}

// ------------------------------------------------------------------
console.log("Pembaca register dasar");
// 118.5 = 0x42ED0000 -> little-endian: 0x0000, 0x42ED (representasi eksak)
check("readFloat32LE membaca 118.5", () => {
  assert.strictEqual(readFloat32LE([0x0000, 0x42ed]), 118.5);
});
check("readUint32LE menggabungkan low + high<<16", () => {
  assert.strictEqual(readUint32LE([1234, 0]), 1234);
  assert.strictEqual(readUint32LE([0, 1]), 65536);
});
check("readInt32LE menangani two's complement", () => {
  assert.strictEqual(readInt32LE([0xffff, 0xffff]), -1);
  assert.strictEqual(readInt32LE([100, 0]), 100);
});

// ------------------------------------------------------------------
console.log("\nDecode per model (register tidak berurutan diuji)");

// Elite440: P aktif di addr 12, Active energy di addr 40 (lompatan!)
check("Elite440: nilai float pada addr 12 terbaca benar", () => {
  const words = new Array(50).fill(0);
  words[12] = 0x0000;
  words[13] = 0x42ed; // 118.5 kW
  words[40] = 1234; // kWh (uint32, addr 40)
  words[41] = 0;
  const d = decode(PROFILES["CEWE Elite440"], words);
  assert.strictEqual(d["P aktif"].value, 118.5);
  assert.strictEqual(d["P aktif"].unit, "kW");
  assert.strictEqual(d["Active energy import"].value, 1234);
});

check("Elite440: register yang tidak ikut terbaca dilewati", () => {
  const words = new Array(14).fill(0); // hanya sampai addr 13
  const d = decode(PROFILES["CEWE Elite440"], words);
  assert.ok(d["P aktif"], "P aktif harus ada");
  assert.ok(!d["Active energy import"], "kWh harus dilewati, bukan error");
});

check("AMC96: integer berskala 10 -> engineering", () => {
  const words = [
    4000, 3990, 3980, // U L1..L3 (skala 10)
    1824, 1131, 804, // I L1..L3 (skala 100)
    1186, 430, 1262, // P=11.86? tidak: skala 10 -> 118.6 kW
    94, // PF skala 100 -> 0.94
    500, // Hz skala 10 -> 50.0
  ];
  const d = decode(PROFILES["ACREL AMC96"], words);
  assert.strictEqual(d["U L1"].value, 400);
  assert.strictEqual(d["I L1"].value, 18.24);
  assert.strictEqual(d["P aktif"].value, 118.6);
  assert.strictEqual(d["PF"].value, 0.94);
  assert.strictEqual(d["Frekuensi"].value, 50);
});

check("DMG510: int32 skala 100 & PF int16 skala 1000", () => {
  const p = PROFILES["LOVATO DMG510"];
  const base = 3000;
  const rel = (addr) => addr - base;
  const words = new Array(200).fill(0);
  words[rel(3006)] = 1186; // P aktif low word
  words[rel(3006) + 1] = 0;
  words[rel(3012)] = 940; // PF skala 1000 -> 0.94
  const d = decode(p, words, base);
  assert.strictEqual(d["P aktif"].value, 11.86);
  assert.strictEqual(d["PF"].value, 0.94);
});

check("EM220: uint32 skala 1000", () => {
  const words = new Array(30).fill(0);
  words[6] = 26500; // P aktif = 26.5 kW
  const d = decode(PROFILES["WEIDMULLER EM220"], words);
  assert.strictEqual(d["P aktif"].value, 26.5);
});

// ------------------------------------------------------------------
console.log("\nParameter turunan");
check("derive: PF = kW / kVA", () => {
  const d = derive({ "P aktif": { value: 94 }, "S semu": { value: 100 } });
  assert.strictEqual(d.powerFactor, 0.94);
});
check("derive: kVAh = kWh / PF", () => {
  const d = derive({
    "P aktif": { value: 94 },
    "S semu": { value: 100 },
    "Active energy import": { value: 1000 },
  });
  assert.strictEqual(d.energyApparent, 1063.83);
});
check("derive: tidak crash saat kVA = 0", () => {
  const d = derive({ "P aktif": { value: 0 }, "S semu": { value: 0 } });
  assert.ok(d.powerFactor === null || d.powerFactor === 0);
});

// ------------------------------------------------------------------
console.log("\nIntegritas registry");
check("5 model terdaftar", () => {
  assert.strictEqual(Object.keys(PROFILES).length, 5);
});
check("18 device punya mapping model", () => {
  assert.strictEqual(Object.keys(DEVICE_MODEL).length, 18);
});
check("semua device punya model yang valid", () => {
  for (const [id, model] of Object.entries(DEVICE_MODEL)) {
    assert.ok(PROFILES[model], `${id} -> model "${model}" tidak dikenal`);
  }
});
check("hanya PAC3220 yang punya register kVAh native", () => {
  const withKVAh = Object.values(PROFILES).filter(
    (p) => p.available.includes("kVAh"),
  );
  assert.strictEqual(withKVAh.length, 1);
  assert.strictEqual(withKVAh[0].model, "SIEMENS PAC3220");
});
check("hanya EM220 yang tanpa dukungan THD", () => {
  const withoutTHD = Object.values(PROFILES).filter(
    (p) => !p.available.includes("THD-i"),
  );
  assert.strictEqual(withoutTHD.length, 1);
  assert.strictEqual(withoutTHD[0].model, "WEIDMULLER EM220");
});
check("register energy selalu 2 register (32-bit)", () => {
  for (const p of Object.values(PROFILES)) {
    for (const r of p.registers) {
      if (/energy/i.test(r.label)) {
        assert.strictEqual(r.count, 2, `${p.model} / ${r.label}`);
        assert.ok(["uint32", "int32"].includes(r.type), `${p.model} / ${r.label}`);
      }
    }
  }
});
check("count register konsisten dengan tipe datanya", () => {
  for (const p of Object.values(PROFILES)) {
    for (const r of p.registers) {
      const need = ["uint32", "int32", "float32", "float64"].includes(r.type)
        ? 2
        : 1;
      assert.strictEqual(
        r.count,
        need,
        `${p.model} / ${r.label} (${r.type}) count=${r.count}, harusnya ${need}`,
      );
    }
  }
});
check("register tidak saling bertumpuk", () => {
  for (const p of Object.values(PROFILES)) {
    const sorted = [...p.registers].sort((a, b) => a.addr - b.addr);
    for (let i = 1; i < sorted.length; i++) {
      const prev = sorted[i - 1];
      assert.ok(
        prev.addr + prev.count <= sorted[i].addr,
        `${p.model}: ${prev.label} (addr ${prev.addr}) menabrak ${sorted[i].label} (addr ${sorted[i].addr})`,
      );
    }
  }
});
check("tidak ada dua register dengan alamat sama", () => {
  for (const p of Object.values(PROFILES)) {
    const addrs = p.registers.map((r) => r.addr);
    assert.strictEqual(
      new Set(addrs).size,
      addrs.length,
      `${p.model} punya alamat register duplikat`,
    );
  }
});
check("register kVAh hanya di PAC3220", () => {
  for (const p of Object.values(PROFILES)) {
    const has = p.registers.some((r) => /kVAh/i.test(r.unit));
    assert.strictEqual(
      has,
      p.model === "SIEMENS PAC3220",
      `${p.model} punya/tidak punya register kVAh`,
    );
  }
});
check("semua register punya scale > 0", () => {
  for (const p of Object.values(PROFILES)) {
    for (const r of p.registers) {
      assert.ok(r.scale > 0, `${p.model} / ${r.label} scale=${r.scale}`);
    }
  }
});

console.log(`\n${passed} test lulus.`);
