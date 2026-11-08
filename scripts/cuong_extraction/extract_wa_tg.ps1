# PowerShell Forensic Extraction & Full Dump Packaging Script (Task 1 - Cuong)
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\scripts\cuong_extraction\extract_wa_tg.ps1
#
# Performs two functions on the rooted DiFo AVD:
#   1. Pulls WhatsApp (msgstore.db, wa.db, files/key) and Telegram (cache4.db, userconfing.xml)
#      plus any companion -wal/-shm/-journal files, verifying on-device vs. local SHA-256
#      and logging every artifact to .\results\hash_table.csv.
#   2. Packages full /data/data tar archives (cache/, shared_prefs/, files/, Avatars/)
#      under .\dumps\for_hai\ for Task 3 (Hai's non-DB artifact & timeline analysis).

param(
    [string]$OutDir = ".\dumps",
    [string]$AdbExe = "D:\Android\Sdk\platform-tools\adb.exe"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $AdbExe)) {
    $AdbExe = "adb"
}

$WaDir  = Join-Path $OutDir "whatsapp"
$TgDir  = Join-Path $OutDir "telegram"
$HaiDir = Join-Path $OutDir "for_hai"
New-Item -ItemType Directory -Force -Path $WaDir, $TgDir, $HaiDir, ".\results" | Out-Null

$HashCsv = ".\results\hash_table.csv"
if (-not (Test-Path $HashCsv)) {
    "timestamp_utc,member,app_or_source,device_path,local_file,size_bytes,sha256_on_device,sha256_after_pull,match_status" |
        Out-File -FilePath $HashCsv -Encoding utf8
}

$Timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

Write-Host "[*] Ensuring adbd is running as root..." -ForegroundColor Cyan
& $AdbExe root | Out-Null
& $AdbExe wait-for-device

function Pull-And-Verify {
    param(
        [string]$App,
        [string]$RemotePath,
        [string]$LocalDir
    )
    $Exists = (& $AdbExe shell "if [ -f '$RemotePath' ]; then echo YES; else echo NO; fi").Trim()
    if ($Exists -ne "YES") {
        Write-Host "  [-] Not present on device (skipped): $RemotePath" -ForegroundColor DarkGray
        return
    }
    $BaseName = Split-Path $RemotePath -Leaf
    $LocalPath = Join-Path $LocalDir $BaseName

    $RemoteHashLine = (& $AdbExe shell "sha256sum '$RemotePath'").Trim()
    $RemoteHash = ($RemoteHashLine -split "\s+")[0].ToLower()

    & $AdbExe pull $RemotePath $LocalPath | Out-Null
    $LocalHash = (Get-FileHash -Algorithm SHA256 $LocalPath).Hash.ToLower()
    $SizeBytes = (Get-Item $LocalPath).Length

    $Status = if ($RemoteHash -eq $LocalHash) { "MATCH" } else { "MISMATCH" }
    "$Timestamp,Cuong,$App,$RemotePath,$LocalPath,$SizeBytes,$RemoteHash,$LocalHash,$Status" |
        Out-File -FilePath $HashCsv -Append -Encoding utf8
    Write-Host "  [+] $BaseName ($Status, $SizeBytes bytes): $LocalHash" -ForegroundColor Green
}

Write-Host "[*] Pulling WhatsApp primary artifacts..." -ForegroundColor Cyan
foreach ($ext in @("", "-wal", "-shm", "-journal")) {
    Pull-And-Verify -App "WhatsApp" -RemotePath "/data/data/com.whatsapp/databases/msgstore.db$ext" -LocalDir $WaDir
    Pull-And-Verify -App "WhatsApp" -RemotePath "/data/data/com.whatsapp/databases/wa.db$ext" -LocalDir $WaDir
}
Pull-And-Verify -App "WhatsApp" -RemotePath "/data/data/com.whatsapp/files/key" -LocalDir $WaDir

Write-Host "[*] Detecting installed Telegram package..." -ForegroundColor Cyan
$TgPkg = "org.telegram.messenger.web"
$CheckWeb = (& $AdbExe shell "if [ -d '/data/data/org.telegram.messenger.web' ]; then echo YES; else echo NO; fi").Trim()
if ($CheckWeb -ne "YES") {
    $TgPkg = "org.telegram.messenger"
}
Write-Host "  [*] Using Telegram package: $TgPkg"

foreach ($ext in @("", "-wal", "-shm", "-journal")) {
    Pull-And-Verify -App "Telegram" -RemotePath "/data/data/$TgPkg/files/cache4.db$ext" -LocalDir $TgDir
}
Pull-And-Verify -App "Telegram" -RemotePath "/data/data/$TgPkg/shared_prefs/userconfing.xml" -LocalDir $TgDir

Write-Host "[*] Packaging full /data/data archives for Hai (Task 3 - Non-DB Artifacts)..." -ForegroundColor Cyan
foreach ($pkg in @("com.whatsapp", $TgPkg, "com.zing.zalo")) {
    $PkgExists = (& $AdbExe shell "if [ -d '/data/data/$pkg' ]; then echo YES; else echo NO; fi").Trim()
    if ($PkgExists -eq "YES") {
        $RemoteTar = "/data/local/tmp/${pkg}_datadump.tar.gz"
        & $AdbExe shell "tar -czf '$RemoteTar' -C /data/data '$pkg' 2>/dev/null || true"
        Pull-And-Verify -App "FullDump_$pkg" -RemotePath $RemoteTar -LocalDir $HaiDir
        & $AdbExe shell "rm -f '$RemoteTar'"
    }
}

Write-Host "`n[+] Extraction complete! Integrity hashes appended to $HashCsv" -ForegroundColor Green
Write-Host "[+] Full dumps for Hai saved under $HaiDir (upload to Team Google Drive -> 03_Raw_Evidence_Dumps/)" -ForegroundColor Yellow
