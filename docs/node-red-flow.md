# Node-RED — tidak dipakai

Akuisisi Modbus dipindah ke worker Python:

- Profil & decoder: `backend/app/acquisition/profiles.py`, `decoder.py`
- Poller: `backend/app/acquisition/poller.py` (`pymodbus`)
- Publish MQTT: `python -m app.acquisition`

Folder `node-red/` masih berisi profil JS lama sebagai arsip; sumber kebenaran
untuk runtime adalah kode Python di `backend/`.
