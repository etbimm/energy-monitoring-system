---
description: "Use when adding or changing calculations, formulas, aggregation, thresholds, or derived metrics in EMS code or SQL."
applyTo: ["backend/**/*.py", "frontend/src/**/*.ts", "frontend/src/**/*.tsx", "database/**/*.sql"]
---

# Perhitungan EMS

- When adding or changing a calculation, update [`docs/calculations.md`](../../docs/calculations.md) in the same change.
- Record the implemented formula, input guards/thresholds, every relevant usage location, and whether it applies to live telemetry, aggregation/UI, or demo data.
- Verify the documentation against the implementation; do not treat design notes or comments as proof of runtime behavior.
