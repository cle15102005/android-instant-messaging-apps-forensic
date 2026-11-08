# Rooted Android 11 AVD Setup & Version Pinning (`SETUP_AVD.md`)

This document specifies how to recreate the controlled Android 11 Virtual Device (`DiFo`) used across all experiments, and records exact versions/hashes for reproducibility.

---

## 1. Host & Android SDK Requirements

| Component | Required Configuration | Verification Command (PowerShell) | Actual Pinned Value |
|---|---|---|---|
| Host OS | Windows 10/11 64-bit (WHPX enabled) | `winver` / `emulator -accel-check` | `Windows 10.0.26200` (`WHPX 10.0.26200 usable`) |
| OpenJDK | JDK 17 LTS (Portable on `D:\Android\jdk-17`) | `java -version` | `OpenJDK 17.0.21.0.2+1-LTS` (Microsoft-15779939) |
| SDK Platform-Tools (`adb`) | Latest | `adb version` | `1.0.41` (`Version 37.0.1-15733141`) |
| Android Emulator | Latest | `emulator -version` | `37.2.13.0` (`build_id 16740729`) |
| SDK Build-Tools (`aapt`) | `build-tools;34.0.0` | `sdkmanager --list_installed` | `34.0.0` |
| System Image | `system-images;android-30;google_apis;x86_64` | `sdkmanager --list_installed` | `android-30;google_apis;x86_64` |

> **Important:** Always select **Google APIs Intel x86 Atom_64 System Image** (API 30). Do **NOT** use the *Google Play* image because production Google Play images disable `adb root`.

---

## 2. Creating and Starting the `DiFo` AVD (CLI-First on `D:\Android`)

To keep drive `C:` clean, all SDK packages, Portable JDK 17, and AVD disk images (`ANDROID_AVD_HOME`) are stored under `D:\Android`.

### Automated One-Command Setup (Recommended)
Run the automated PowerShell script from the repository root:
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\cuong_extraction\setup_android_cli.ps1
```
This script automatically:
1. Downloads Portable OpenJDK 17 to `D:\Android\jdk-17`
2. Downloads Android Command-line Tools to `D:\Android\Sdk\cmdline-tools\latest`
3. Sets `ANDROID_SDK_ROOT=D:\Android\Sdk` and `ANDROID_AVD_HOME=D:\Android\avd`
4. Installs `platform-tools`, `emulator`, `build-tools;34.0.0`, `platforms;android-30`, and `system-images;android-30;google_apis;x86_64`
5. Creates the `DiFo` AVD (`pixel_4`, 4096 MB RAM, 8192 MB storage) inside `D:\Android\avd\DiFo.avd`

### Launching the AVD and Verifying Root
```powershell
# Start the emulator (keep this window open)
D:\Android\Sdk\emulator\emulator.exe -avd DiFo -writable-system

# In a second terminal, verify root privileges and Android version:
adb devices
adb root
adb shell id
# Expected output: uid=0(root) gid=0(root) contexts=u:r:su:s0
adb shell getprop ro.build.version.release
# Expected output: 11
```

---

## 3. Pinned APK Registry

Download APKs from APKMirror, verify their SHA-256 hashes before installation, and record the exact values below:

```powershell
Get-FileHash -Algorithm SHA256 .\apks\<filename>.apk
```

| App | Package Name | `versionName` | `versionCode` | ABI | APK SHA-256 | Source URL | Telegram `LAYER` | `allowBackup` |
|---|---|---|---|---|---|---|---|---|
| **WhatsApp** | `com.whatsapp` | `2.26.44.71` | `264407138` | `arm64-v8a`, `armeabi-v7a`, `x86`, `x86_64` | `fdc09052adb72e97f42661dddd28d06ea19c3ca2a83b2967064a2169d4afef28` | `whatsapp.com/android` | N/A | `true` (`SystemBackupAgent` + `fullBackupContent` excludes DB) |
| **Telegram** | `org.telegram.messenger.web` | `13.2.0` | `72809` | `arm64-v8a`, `armeabi-v7a`, `x86`, `x86_64` | `2d1fe6650578aa4e3437c9e775a7e849837f604a7294c6bd66f971d6ba13470e` | `telegram.org/android` | **`233`** (`TLRPC.LAYER`) | `true` (`BackupAgent` excludes `cache4.db`) |
| **Zalo** | `com.zing.zalo` | `26.10.02` | `261002903` | `arm64-v8a`, `armeabi-v7a` (split APKs) | `20f9f4eb76393af3b2a73d6d483ad93b6f69703d645f362c79ddafe592cfacff` (`base.apk`) | APKMirror (`.apkm` `b4883ce3...`) | N/A | `false` (`0x0`, `ZaloBackupAgent`) |

---

## 4. Snapshot Naming Convention

To guarantee deterministic state preservation (especially for Deleted Data Recovery in §4.2), save AVD snapshots after each ground-truth action:

```powershell
adb emu avd snapshot save step_1_baseline
adb emu avd snapshot save step_2_populated
adb emu avd snapshot save step_3_deleted_tc1
adb emu avd snapshot save step_4_checkpoint_deleted_tc2
adb emu avd snapshot save step_5_vacuum_tc3
adb emu avd snapshot list
```
