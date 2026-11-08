# Empirical Lab Notes & Forensic Findings (`LAB_NOTES_AND_FINDINGS.md`)

This document records all empirical observations, cryptographic hashes, manifest configurations, and SQLite header measurements obtained during the setup and execution phases on our rooted Android 11 Virtual Device (`DiFo`). Every finding below serves as direct evidence for **Sections 2, 3, 4, and 5** of the final LaTeX report.

---

## 1. Controlled Testbed & Version Pinning Summary (§3 Methodology)

To eliminate host drive `C:` storage pressure and guarantee cross-member reproducibility without installing the full Android Studio IDE, the entire forensic testbed was provisioned using a deterministic CLI script ([`scripts/cuong_extraction/setup_android_cli.ps1`](../scripts/cuong_extraction/setup_android_cli.ps1)) under `D:\Android`:

| Component | Pinned Version / Identifier | Forensic Relevance |
|---|---|---|
| **Host OS & Hypervisor** | `Windows 10.0.26200` (`WHPX 10.0.26200 usable`) | Hardware-accelerated x86_64 execution |
| **Java Runtime** | `OpenJDK 17.0.21.0.2+1-LTS` (`Microsoft-15779939`) | Required for `sdkmanager`, `avdmanager`, and **FQLite** |
| **Android Debug Bridge (`adb`)** | `1.0.41` (`Version 37.0.1-15733141`) | Supports `adb root`, `adb pull`, and `adb emu` stimulus |
| **Android Emulator** | `37.2.13.0` (`build_id 16740729`) | Supports deterministic VM snapshots (`adb emu avd snapshot`) |
| **System Image** | `system-images;android-30;google_apis;x86_64` | Android 11 (API 30) **Google APIs** build includes `su` (`uid=0(root)`) and `libndk_translation` for ARM split APKs |
| **AVD Configuration (`DiFo`)** | `pixel_4` profile, `4096 MB` RAM, `8192 MB` data partition | Stored at `D:\Android\avd\DiFo.avd` |
| **Snapshots Captured** | `step_1_baseline`, `step_1b_apps_installed` | Verified via `adb emu avd snapshot save` |

---

## 2. Finding #1: Why `adb backup` Fails on Modern IM Apps (§4.1 & §5 Discussion)

Prior literature (`P03` Rathi et al., 2018; `P10` Zalo 2020 write-up) relied on `adb backup` for unrooted acquisition. Static inspection of `AndroidManifest.xml` across our three pinned APKs using `aapt dump xmltree` ([`results/allowbackup_result.csv`](../results/allowbackup_result.csv)) revealed **three distinct defense mechanisms** that render `adb backup` ineffective even on Android 11 (API 30):

| Application | Package Name | Version (`versionCode`) | `targetSdk` | `android:allowBackup` | `android:backupAgent` & Exclusion Mechanism |
|---|---|---|---|---|---|
| **WhatsApp** | `com.whatsapp` | `2.26.44.71` (`264407138`) | `36` | `true` (`0xffffffff`) | Declares `com.whatsapp.infra.backup.system.SystemBackupAgent`, `fullBackupOnly=true`, and `fullBackupContent=@0x7f180003`, which explicitly excludes `msgstore.db` and `files/key` from local ADB backups. |
| **Telegram** | `org.telegram.messenger.web` | `13.2.0` (`72809`) | `36` | `true` (`0xffffffff`) | Declares `org.telegram.messenger.BackupAgent`, restricting key-value backup and omitting `files/cache4.db`. |
| **Zalo** | `com.zing.zalo` | `26.10.02` (`261002903`) | `36` | **`false` (`0x0`)** | Hard-disables `allowBackup=false` in the manifest alongside `com.zing.zalo.db.backup.ZaloBackupAgent`. **This empirically refutes the 2020 `P10` `adb backup` workflow for modern Zalo versions.** |

Furthermore, all three applications compile against `targetSdkVersion = 36` (Android 16), meaning on Android 12+ (`API >= 31`) the OS itself blocks `adb backup` regardless of manifest flags. Consequently, **rooted `/data/data` acquisition (`adb root` + `adb pull`) is mandatory** for complete database extraction.

---

## 3. Finding #2: Telegram Direct APK Package Naming & TL Layer `233` (§2.2 & §4.1)

1. **Package Identifier Difference (`org.telegram.messenger.web`):**
   - The official standalone APK distributed directly by Telegram (`https://telegram.org/android`, `v13.2.0`, SHA-256 `2d1fe665...`) uses the package name **`org.telegram.messenger.web`** rather than the Google Play Store identifier `org.telegram.messenger` (to enable built-in auto-updates outside Google Play).
   - Forensic tools with hardcoded `/data/data/org.telegram.messenger` paths (as warned in `P07` Arkan & Yurekten) will fail to locate artifacts unless they check both package directories. Our extraction scripts (`extract_wa_tg.sh` and `extract_wa_tg.ps1`) automatically detect both paths.
2. **Exact Type Language (TL) Schema Layer (`TLRPC.LAYER = 233`):**
   - By parsing the Dalvik Executable (`classes.dex`) `class_def` and `encoded_array` static initializers of `Lorg/telegram/tgnet/TLRPC;`, we extracted the exact protocol layer and message bitmask flags for `v13.2.0`:
     - **`TLRPC.LAYER` (Field `#34064`)** = **`233`**
     - `MESSAGE_FLAG_FWD` = `4` (`0x4`)
     - `MESSAGE_FLAG_REPLY` = `8` (`0x8`)
     - `MESSAGE_FLAG_HAS_MARKUP` = `64` (`0x40`)
     - `MESSAGE_FLAG_HAS_ENTITIES` = `128` (`0x80`)
     - `MESSAGE_FLAG_HAS_FROM_ID` = `256` (`0x100`)
     - `MESSAGE_FLAG_HAS_MEDIA` = `512` (`0x200`)
     - `MESSAGE_FLAG_HAS_VIEWS` = `1024` (`0x400`)
     - `MESSAGE_FLAG_HAS_BOT_ID` = `2048` (`0x800`)
     - `MESSAGE_FLAG_EDITED` = `32768` (`0x8000`)
3. **Schema Evolution (`messages` → `messages_v2`):**
   - Confirming `classes.dex` string references at offset `9115207`, modern Telegram stores chat records in `messages_v2` inside `cache4.db`, replacing the legacy `messages` table analyzed by Anglano et al. (`P01`, 2017).

---

## 4. Finding #3: Android 11 Telephony & Call Log Storage Internals (§2.5 & §4.2)

Direct inspection of `/data/data/com.android.providers.telephony/databases/` and `/data/data/com.android.providers.contacts/databases/` on the clean Android 11 AVD (`step_1_baseline`) revealed two critical facts for **Task 2 (Linh - Deleted Data Recovery)**:

1. **Dedicated `calllog.db` Database:**
   - `/data/data/com.android.providers.contacts/databases/` contains **`calllog.db`**, `contacts2.db`, and `profile.db` as separate SQLite files. Older forensic guides citing `contacts2.db` for call history are outdated on Android 11.
2. **Default Journal Mode (`-journal` vs. `-wal`):**
   - Both `mmssms.db` and `calllog.db` on Android 11 default to **Rollback Journal mode** (`mmssms.db-journal`, `calllog.db-journal`; SQLite header offsets `18` and `19` = `0x01`), whereas WhatsApp (`msgstore.db`) and Telegram (`cache4.db`) operate in **Write-Ahead Logging (`WAL`) mode** (offsets `18` and `19` = `0x02`).
   - **Forensic Implication:** When an SMS or Call Log entry is deleted under default rollback journal mode, no `-wal` file exists; recovery must target **Freelist pages and unallocated cell areas** within the main `.db` file using FQLite (`P13`), unless WAL mode is active. Conversely, in WAL-enabled databases (`msgstore.db`, `cache4.db`, or WAL-switched `mmssms.db`), prior uncommitted/uncheckpointed frames remain in the `-wal` file even if `SQLITE_SECURE_DELETE` zeroes out the active B-tree page (`P12`).
