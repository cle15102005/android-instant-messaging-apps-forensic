# Forensic Analysis of Instant Messaging Applications on Android Devices

Digital forensics toolkit and reproducibility artifacts for analyzing **WhatsApp**, **Telegram**, **Zalo**, and **deleted SMS/Call Logs** on a rooted Android 11 AVD (`Google APIs Intel x86 Atom_64`).

## Objectives

1. **Android IM Extraction & Reconstruction (WhatsApp + Telegram):** Identify artifact paths, pull databases via `adb root`, parse Telegram `messages_v2` TL binary blobs, reconstruct contacts/chats/call logs, and verify SHA-256 integrity.
2. **Deleted Data Recovery (SMS + Call Logs):** Recover deleted records from `mmssms.db` and `calllog.db` using a WAL-first strategy (`WAL → Freelist`) via FQLite across three checkpoint/VACUUM test cases (`TC1`, `TC2`, `TC3`).
3. **App Artifacts Analysis (Cache, Shared_Prefs, Media):** Enumerate non-database artifacts across WhatsApp, Telegram, and Zalo (including `.trash` and `shared_prefs`), and build a cross-app forensic timeline.
4. **Zalo Deep Dive (Novelty):** Apply peer-reviewed mobile forensic methodology (`P01–P07`) to Zalo on Android (`v24.x`), verify multi-file database structure (`P09`), and inspect encryption status (`Plan A/B/C`).

## Repository Structure

```text
android-instant-messaging-apps-forensic/
├── README.md                  # Project overview & quickstart
├── SETUP_AVD.md               # Rooted Android 11 AVD setup & version pinning
├── Dockerfile                 # Reproducible Python environment for analysis scripts
├── requirements.txt           # Pinned Python dependencies
├── docs/                      # Task plan, environment registry, and literature matrix (.xlsx)
├── schemas/                   # Ground-truth scenario & standardized CSV schemas
├── sample_data/               # Sanitized sample databases for Docker verification
├── scripts/
│   ├── cuong_extraction/      # WhatsApp/Telegram extraction, TL parser, allowBackup check
│   ├── linh_recovery/         # SQLite header checker & WAL/Freelist recovery parser
│   ├── hai_artifacts/         # Non-DB artifact enumerator & cross-app timeline builder
│   └── huy_zalo/              # Zalo structure verifier & Frida SQLCipher key hook
└── results/                   # Final CSV tables, reconstruction logs, and plots
```

## Quickstart (Reproducible Docker Environment)

The Docker container bundles all Python analysis scripts and sanitized sample data (the Android Emulator itself runs on the Windows host as documented in [SETUP_AVD.md](SETUP_AVD.md)).

```bash
# Build the analysis image
docker build -t im-forensics:latest .

# Verify scripts inside the container
docker run --rm im-forensics:latest python scripts/linh_recovery/sqlite_header_check.py --help
```

## Team & Roles

| Member | Role | Target / Scope | Report Sections |
|---|---|---|---|
| **Cường** | Android Extraction & Reconstruction | WhatsApp (`msgstore.db`, `wa.db`) & Telegram (`cache4.db`, `messages_v2`) | Theory §2.1–2.2, Impl §4.1 |
| **Linh** | Deleted Data Recovery | `mmssms.db` & `calllog.db` (`WAL → Freelist`, `TC1–TC3`) | Theory §2.5, Impl §4.2 |
| **Hải** | App Artifacts Analysis | Cache, `shared_prefs`, Media, `.trash`, Cross-app Timeline | Impl §4.3 |
| **Huy** | Zalo Deep Dive (Novelty) | Zalo Android `v24.x` (`databases/zalo`, `<UID>/<chatID>.db`) | Theory §2.3, Impl §4.4 |
| **All** | Report & Presentation | Literature Matrix (`P01–P13`), Comparison (§2.4), Docker & Slides | §1, §2.4, §3, §5 |
