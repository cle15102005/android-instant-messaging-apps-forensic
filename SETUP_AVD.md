# Rooted Android 11 AVD Setup & Version Pinning (`SETUP_AVD.md`)

This document specifies how to recreate the controlled Android 11 Virtual Device (`DiFo`) used across all experiments, and records exact versions/hashes for reproducibility.

---

## 1. Host & Android SDK Requirements

| Component | Required Configuration | Verification Command (PowerShell) | Actual Pinned Value |
|---|---|---|---|
| Host OS | Windows 10/11 64-bit (WHPX enabled) | `winver` | *(fill during setup)* |
| Android Studio | Latest Stable | `Help > About` | *(fill during setup)* |
| SDK Platform-Tools (`adb`) | Latest | `adb version` | *(fill during setup)* |
| Android Emulator | Latest | `emulator -version` | *(fill during setup)* |
| SDK Build-Tools (`aapt`) | Latest | `sdkmanager --list_installed` | *(fill during setup)* |
| System Image | `system-images;android-30;google_apis;x86_64` | `sdkmanager --list_installed` | Revision: *(fill)* |

> **Important:** Always select **Google APIs Intel x86 Atom_64 System Image** (API 30). Do **NOT** use the *Google Play* image because production Google Play images disable `adb root`.

---

## 2. Creating and Starting the `DiFo` AVD

1. Open **Android Studio** → **Virtual Device Manager** → **Create Device**:
   - **Hardware Profile:** Pixel 4
   - **System Image:** Android 11.0 (R), API Level 30, ABI `x86_64`, Target `Google APIs`
   - **AVD Name:** `DiFo`
   - **RAM:** 4096 MB | **Internal Storage:** 8192 MB
2. Launch the AVD and verify root privileges:
   ```powershell
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
| **WhatsApp** | `com.whatsapp` | *(fill)* | *(fill)* | *(fill)* | *(fill)* | APKMirror | N/A | *(fill)* |
| **Telegram** | `org.telegram.messenger` | *(fill)* | *(fill)* | *(fill)* | *(fill)* | APKMirror | *(fill)* | *(fill)* |
| **Zalo** | `com.zing.zalo` | *(fill)* | *(fill)* | *(fill)* | *(fill)* | APKMirror | N/A | *(fill)* |

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
