# Requires PowerShell 5.1+ on Windows 10/11 (x64)
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\scripts\cuong_extraction\setup_android_cli.ps1
#
# Everything (Portable JDK 17, Android SDK, System Image, and AVD disk images)
# is placed under D:\Android so drive C: is NOT consumed.

$ErrorActionPreference = "Stop"

$BaseDir    = "D:\Android"
$JdkRoot    = "$BaseDir\jdk-17"
$SdkRoot    = "$BaseDir\Sdk"
$AvdHome    = "$BaseDir\avd"
$DownloadDir = "$BaseDir\downloads"
$AvdName    = "DiFo"
$SysImgPkg  = "system-images;android-30;google_apis;x86_64"

Write-Host "=== [1/6] Creating directory structure on D:\Android ===" -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path $BaseDir, $SdkRoot, $AvdHome, $DownloadDir | Out-Null

# 1. Portable OpenJDK 17 (Microsoft Build of OpenJDK 17 x64 ZIP)
$JavaExe = Get-ChildItem -Path $JdkRoot -Filter "java.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $JavaExe) {
    Write-Host "=== [2/6] Downloading Portable OpenJDK 17 to $JdkRoot ===" -ForegroundColor Cyan
    $JdkZip = "$DownloadDir\openjdk-17-windows-x64.zip"
    $JdkUrl = "https://aka.ms/download-jdk/microsoft-jdk-17-windows-x64.zip"
    if (-not (Test-Path $JdkZip)) {
        curl.exe -L --fail --retry 3 -o $JdkZip $JdkUrl
    }
    New-Item -ItemType Directory -Force -Path $JdkRoot | Out-Null
    Expand-Archive -Path $JdkZip -DestinationPath $JdkRoot -Force
    $JavaExe = Get-ChildItem -Path $JdkRoot -Filter "java.exe" -Recurse | Select-Object -First 1
} else {
    Write-Host "=== [2/6] Portable OpenJDK 17 already present ===" -ForegroundColor Green
}

$JavaHome = Split-Path (Split-Path $JavaExe.FullName -Parent) -Parent
$env:JAVA_HOME = $JavaHome

# 2. Android Command-line Tools (Windows latest)
$SdkManagerBat = "$SdkRoot\cmdline-tools\latest\bin\sdkmanager.bat"
if (-not (Test-Path $SdkManagerBat)) {
    Write-Host "=== [3/6] Downloading Android Command-line Tools to $SdkRoot ===" -ForegroundColor Cyan
    $CmdToolsZip = "$DownloadDir\commandlinetools-win-latest.zip"
    $CmdToolsUrl = "https://dl.google.com/android/repository/commandlinetools-win-11076708_latest.zip"
    if (-not (Test-Path $CmdToolsZip)) {
        curl.exe -L --fail --retry 3 -o $CmdToolsZip $CmdToolsUrl
    }
    $TmpExtract = "$DownloadDir\cmdline-extract"
    if (Test-Path $TmpExtract) { Remove-Item -Recurse -Force $TmpExtract }
    Expand-Archive -Path $CmdToolsZip -DestinationPath $TmpExtract -Force
    $LatestDir = "$SdkRoot\cmdline-tools\latest"
    New-Item -ItemType Directory -Force -Path (Split-Path $LatestDir -Parent) | Out-Null
    if (Test-Path $LatestDir) { Remove-Item -Recurse -Force $LatestDir }
    Move-Item -Path "$TmpExtract\cmdline-tools" -Destination $LatestDir
    Remove-Item -Recurse -Force $TmpExtract
} else {
    Write-Host "=== [3/6] Android Command-line Tools already present ===" -ForegroundColor Green
}

# 3. Set session & user environment variables (all pointing to D:\Android)
$env:ANDROID_HOME = $SdkRoot
$env:ANDROID_SDK_ROOT = $SdkRoot
$env:ANDROID_AVD_HOME = $AvdHome

$ToolPaths = @(
    "$JavaHome\bin",
    "$SdkRoot\cmdline-tools\latest\bin",
    "$SdkRoot\platform-tools",
    "$SdkRoot\emulator",
    "$SdkRoot\build-tools\34.0.0"
)
$env:PATH = ($ToolPaths -join ";") + ";" + $env:PATH

[Environment]::SetEnvironmentVariable("JAVA_HOME", $JavaHome, "User")
[Environment]::SetEnvironmentVariable("ANDROID_HOME", $SdkRoot, "User")
[Environment]::SetEnvironmentVariable("ANDROID_SDK_ROOT", $SdkRoot, "User")
[Environment]::SetEnvironmentVariable("ANDROID_AVD_HOME", $AvdHome, "User")

$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
foreach ($p in $ToolPaths) {
    if ($UserPath -notlike "*$p*") {
        $UserPath = "$p;$UserPath"
    }
}
[Environment]::SetEnvironmentVariable("Path", $UserPath, "User")

# 4. Accept licenses and install required SDK packages
Write-Host "=== [4/6] Accepting SDK licenses & installing Android 11 (API 30) Google APIs x86_64 ===" -ForegroundColor Cyan
1..20 | ForEach-Object { "y" } | & $SdkManagerBat --sdk_root="$SdkRoot" --licenses | Out-Null

& $SdkManagerBat --sdk_root="$SdkRoot" `
    "platform-tools" `
    "emulator" `
    "build-tools;34.0.0" `
    "platforms;android-30" `
    $SysImgPkg

# 5. Create the DiFo AVD (Pixel 4, 4GB RAM, 8GB Internal Storage)
$AvdManagerBat = "$SdkRoot\cmdline-tools\latest\bin\avdmanager.bat"
$AvdIni = "$AvdHome\$AvdName.ini"
if (-not (Test-Path $AvdIni)) {
    Write-Host "=== [5/6] Creating AVD '$AvdName' (Pixel 4, Android 11 Google APIs x86_64) in $AvdHome ===" -ForegroundColor Cyan
    "no" | & $AvdManagerBat create avd --force `
        --name $AvdName `
        --package $SysImgPkg `
        --device "pixel_4" `
        --path "$AvdHome\$AvdName.avd"

    $ConfigIni = "$AvdHome\$AvdName.avd\config.ini"
    if (Test-Path $ConfigIni) {
        Add-Content -Path $ConfigIni -Value "`nhw.ramSize=4096`ndisk.dataPartition.size=8192M`nhw.keyboard=yes"
    }
} else {
    Write-Host "=== [5/6] AVD '$AvdName' already exists at $AvdIni ===" -ForegroundColor Green
}

# 6. Print verification versions for SETUP_AVD.md
Write-Host "`n=== [6/6] Setup Complete! Verification Summary (copy to SETUP_AVD.md) ===" -ForegroundColor Green
Write-Host "JAVA_HOME        : $env:JAVA_HOME"
Write-Host "ANDROID_SDK_ROOT : $env:ANDROID_SDK_ROOT"
Write-Host "ANDROID_AVD_HOME : $env:ANDROID_AVD_HOME"
& "$JavaHome\bin\java.exe" -version
& "$SdkRoot\platform-tools\adb.exe" version
& "$SdkRoot\emulator\emulator.exe" -version | Select-Object -First 4
& "$SdkRoot\emulator\emulator.exe" -accel-check
& "$SdkRoot\emulator\emulator.exe" -list-avds

Write-Host "`nTo launch the AVD:" -ForegroundColor Yellow
Write-Host "  D:\Android\Sdk\emulator\emulator.exe -avd DiFo -writable-system"
Write-Host "Then in another terminal, test root:" -ForegroundColor Yellow
Write-Host "  adb root && adb shell id"
