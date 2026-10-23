# Retry wrapper untuk npm install di koneksi yang tidak stabil.
# Setiap percobaan memanfaatkan npm cache, sehingga percobaan
# berikutnya dilanjutkan dari titik gagal sebelumnya.

$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot

for ($i = 1; $i -le 10; $i++) {
    Write-Host "=== Percobaan $i/10 ===" -ForegroundColor Cyan
    npm.cmd install `
        --fetch-retries=10 `
        --fetch-retry-mintimeout=15000 `
        --fetch-retry-maxtimeout=120000 `
        --fetch-timeout=600000 `
        --maxsockets=2 `
        --no-audit `
        --no-fund

    if ($LASTEXITCODE -eq 0) {
        Write-Host "=== Berhasil pada percobaan $i ===" -ForegroundColor Green
        exit 0
    }

    Write-Host "Gagal, menunggu 10 detik sebelum mencoba lagi..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10
}

Write-Host "=== Gagal setelah 10 percobaan ===" -ForegroundColor Red
exit 1