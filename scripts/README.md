# Scripts

Utilitas pendukung proyek EMS.

## Utilitas

- Backup PostgreSQL: jalankan `py .\scripts\backup_db.py` saat
  service database Docker Compose aktif. File custom-format disimpan di
  `backups/` (diabaikan Git). Parameter opsional:

  ```powershell
  py .\scripts\backup_db.py --database ems --postgres-user ems --output-directory .\backups
  ```

- Data simulator untuk pengembangan dihasilkan oleh worker akuisisi backend
  (`ACQUISITION_MODE=simulator`).
- Ekspor pembacaan ke CSV tersedia di halaman History.