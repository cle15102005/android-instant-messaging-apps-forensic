# Forensic Analysis of Instant Messaging Applications on Android Devices (WhatsApp & Android Telephony)

University Digital Forensics Group Project (`ITE15` — HUST SOICT) investigating **WhatsApp Messenger (`com.whatsapp` v2.26.44.71)** and **Android 11 Telephony (`mmssms.db` & `calllog.db`)** on a rooted Android 11 Virtual Device (`DiFo` AVD) following **NIST SP 800-86**.

---

## 1. Team Workload & Scope Division (4 Members)

| Member | Student ID | Assigned Role & Forensic Pillar | Input Evidence Folder | Output Directory | Status |
| :--- | :---: | :--- | :--- | :--- | :---: |
| **Le Viet Cuong** | `20235586` | **Role 1:** Testbed Setup, `allowBackup` Audit, Root Acquisition (SHA-256 Chain of Custody) & Active Chat/Contact/Call Reconstruction | `dumps/whatsapp/` | `results/reconstruction_logs/whatsapp/` & `results/hash_table.csv` | **COMPLETED (100%)** |
| **Hoang Quoc Huy** | `20235594` | **Role 2:** Signal Protocol E2EE Database (`axolotl.db`), Local Backup Key (`files/key` 158B) & Auxiliary WhatsApp SQLite DBs (`status.db`, `stickers.db`, `chatsettings.db`, `companion_devices.db`, `media.db`, `sync.db`) | `dumps/for_huy/` | `results/reconstruction_logs/huy_crypto_dbs/` | **PENDING (Huy)** |
| **Nguyen Ngoc Linh** | `20235599` | **Role 3:** Deleted Message, Call Log & SMS Recovery — Pre-Checkpoint WAL Comparison (`msgstore.db-wal`, `wa_calllog_dummy.db-wal`) & Post-Checkpoint B-Tree Freeblock Carving (`mmssms.db`, `calllog.db`) | `dumps/for_linh/` | `results/carved_sms_calls/` | **PENDING (Linh)** |
| **Dinh Ha Hai** | `20235589` | **Role 4:** Non-Database Artifacts (`shared_prefs/*.xml`, `cache/`, EXIF Stripping on Sent Media, `files/.trash/` Deletion Staging) & Unified Timeline Correlation | `dumps/for_hai/` | `results/timeline/` | **PENDING (Hai)** |

---

## 2. Repository Structure

```text
project/
├── docs/
│   ├── IM_Forensics_Literature_Matrix.xlsx     # 8 WhatsApp & SQLite/SMS papers (W01-W08) + Methods Synthesis
│   ├── IM_Forensics_Task_Plan_1Month.xlsx      # 4-member task breakdown & status tracking
│   ├── IM_Forensics_Environment_Versions.xlsx  # Testbed & 18 WhatsApp SQLite DB inventory
│   └── LAB_NOTES_AND_FINDINGS.md               # Empirical notes & handoff specifications
├── scripts/
│   ├── cuong_extraction/                       # [COMPLETED] Role 1 scripts (Cuong)
│   │   ├── setup_android_cli.ps1               # Rooted Android 11 DiFo AVD setup
│   │   ├── check_allowbackup.sh                # Manifest allowBackup & BackupAgent audit
│   │   ├── extract_wa_tg.ps1                   # Rooted ADB extraction & SHA-256 hashing
│   │   ├── generate_dummy_calls_sms.py         # Packages team dumps (for_huy, for_linh, for_hai)
│   │   ├── generate_sample_data.py             # Sanitized sample DB generator for CI/Docker
│   │   └── whatsapp_reconstruct.py             # Active contacts, messages & calls reconstruction
│   ├── huy_crypto_dbs/                         # [TODO] Role 2 scripts (Huy)
│   │   └── README_TODO.md                      # Instructions for axolotl.db, key & auxiliary DBs
│   ├── linh_recovery/                          # [TODO] Role 3 scripts (Linh)
│   │   ├── sqlite_header_check.py              # 100-byte SQLite header inspector
│   │   └── README_TODO.md                      # Instructions for WAL & B-Tree freeblock recovery
│   └── hai_artifacts/                          # [TODO] Role 4 scripts (Hai)
│       └── README_TODO.md                      # Instructions for shared_prefs, EXIF, .trash & timeline
├── sample_data/                                # Sanitized SQLite databases safe for public Git
│   ├── whatsapp/                               # Sanitized wa.db & msgstore.db
│   └── telephony/                              # Sanitized mmssms.db & calllog.db
└── results/
    ├── allowbackup_audit.txt                   # Static manifest backup audit output (Cuong)
    ├── hash_table.csv                          # 31 SHA-256 chain-of-custody hashes (Cuong)
    ├── reconstruction_logs/
    │   ├── whatsapp/                           # Active wa_contacts.csv, wa_messages.csv, wa_calls.csv (Cuong)
    │   └── huy_crypto_dbs/                     # Output directory for Huy
    ├── carved_sms_calls/                       # Output directory for Linh
    └── timeline/                               # Output directory for Hai
```

---

## 3. Quick Start & Verification (Role 1 — Completed by Cuong)

1. **Generate or refresh team raw evidence dumps and SHA-256 hash table:**
   ```powershell
   python scripts/cuong_extraction/generate_dummy_calls_sms.py
   ```
2. **Run Cuong's active WhatsApp reconstruction (preserving 100% SHA-256 integrity):**
   ```powershell
   python scripts/cuong_extraction/whatsapp_reconstruct.py --dump-dir ./dumps/whatsapp --out-dir ./results/reconstruction_logs/whatsapp
   ```
3. **Inspect SQLite 100-byte headers (Starter utility for Linh):**
   ```powershell
   python scripts/linh_recovery/sqlite_header_check.py ./dumps/for_linh/msgstore.db ./dumps/for_linh/mmssms.db ./dumps/for_linh/calllog.db
   ```
