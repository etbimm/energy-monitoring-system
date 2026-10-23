# Backend (placeholder)

Backend API untuk EMS. Belum dibuat.

## Rencana Isi

```
backend/
|- src/
|  |- index.ts          # entry point server
|  |- routes/           # endpoint REST
|  |- services/         # logika bisnis + MQTT subscriber
|  |- db/               # koneksi & query database
|  |- ws/               # WebSocket server
|  `- types/
|- package.json
`- tsconfig.json
```

## Tanggung jawab

- Subscribe ke topic MQTT `ems/#`
- Simpan reading ke PostgreSQL
- Menyediakan endpoint REST untuk query historis & ringkasan
- Push data ke frontend via WebSocket
- Menjalankan aturan alarm

## Stack Rencana

- Node.js + TypeScript
- Fastify atau Express
- `mqtt` untuk broker
- `pg` atau Prisma untuk database

Lihat `docs/architecture.md` untuk daftar endpoint yang direncanakan.