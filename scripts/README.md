# Scripts

Utilitas pendukung proyek EMS.

## Utilitas

- Backup PostgreSQL: jalankan `py .\scripts\backup_db.py` saat
  service database Docker Compose aktif. File custom-format disimpan di
  `backups/` (diabaikan Git). Parameter opsional:

  ```powershell
  py .\scripts\backup_db.py --database ems --postgres-user ems --output-directory .\backups
  ```

- Histori dummy 30 hari: `scripts/seed-history.sql`. Hanya untuk database
  pengembangan; **jangan** jalankan di database produksi/meter asli.

  ```bash
  docker compose exec -T db psql -U ems -d ems -v ON_ERROR_STOP=1 < scripts/seed-history.sql
  ```

- Perbaikan counter energi database dummy (lonjakan/penurunan kWh, kVAh lama):
  `scripts/repair-dummy-energy.sql`. **Hanya** untuk database pengembangan;
  hentikan acquisition dulu (petunjuk ada di kepala file).

- Data simulator untuk pengembangan dihasilkan oleh worker akuisisi backend
  (`ACQUISITION_MODE=simulator`).
- Ekspor pembacaan ke CSV tersedia di halaman History.