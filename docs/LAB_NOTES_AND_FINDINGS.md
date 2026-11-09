# Forensic Lab Notes & Empirical Findings (Role 1 Completed — Ready for Roles 2, 3, 4)

## 1. Scope & Justification for Focusing Implementation on WhatsApp (`com.whatsapp` v2.26.44.71)
- **Syllabus Prompt Interpretation:** The project topic (*"Extracting and Analyzing WhatsApp/Telegram/Zalo Chat Databases from an Android/iOS Backup, Recovering Deleted SMS/Call Logs, and Analyzing App Artifacts (Cache, SQLite Databases)"*) uses `/` to denote candidate Instant Messaging platforms and mobile OS testbeds.
- **Empirical Anti-Emulator & Registration Findings on Android 11 AVD (`DiFo`):**
  1. **WhatsApp (`com.whatsapp` v2.26.44.71):** Successfully registered, authenticated, and generated rich forensic evidence across **18 SQLite databases** and **748 sandbox files** (`29.97 MB` compressed in `com.whatsapp_datadump.tar.gz`).
  2. **Telegram (`org.telegram.messenger.web` v13.2.0):** Enforces a paid "One-time SMS Fee (₫18,750)" via Google Play billing for new Vietnamese (`+84`) phone numbers on virtualized devices.
  3. **Zalo (`com.zing.zalo` v26.10.02):** Blocks account registration/login on x86_64 Android emulators with hardware attestation error `(2028): Unable to create a new account on this device`.
- **4-Member Deep-Dive Workload on WhatsApp + Android Telephony:**
  - **Role 1 — Le Viet Cuong (`20235586`) [COMPLETED]:** Testbed setup (`DiFo` AVD), static `allowBackup` audit, live WhatsApp & dummy Call Log/SMS acquisition with SHA-256 chain of custody (`results/hash_table.csv`), and active relational reconstruction (`wa_contacts.csv`, `wa_messages.csv`, `wa_calls.csv`).
  - **Role 2 — Hoang Quoc Huy (`20235594`) [PENDING MEMBER EXECUTION]:** Signal Protocol E2EE database analysis (`axolotl.db` containing `1,624` prekeys, `identities`, `signed_prekeys`), `files/key` (`158 bytes`) structure for `.crypt14/.crypt15`, and auxiliary WhatsApp SQLite databases (`status.db`, `stickers.db`, `chatsettings.db`, `companion_devices.db`, `media.db`, `sync.db`) in `dumps/for_huy/`.
  - **Role 3 — Nguyen Ngoc Linh (`20235599`) [PENDING MEMBER EXECUTION]:** Pre-checkpoint SQLite WAL recovery (`msg_id = 6` in `msgstore.db-wal` and `call_id = 2` in `wa_calllog_dummy.db-wal`) and post-checkpoint B-Tree freeblock carving (`call_id = 4` in `wa_calllog_dummy.db`, deleted SMS `_id = 3, 5` in `mmssms.db`, and deleted calls `_id = 2, 4` in `calllog.db`) in `dumps/for_linh/`.
  - **Role 4 — Dinh Ha Hai (`20235589`) [PENDING MEMBER EXECUTION]:** Non-database artifacts (`shared_prefs/*.xml`, `cache/Profile Pictures/`, EXIF stripping on `IMG-20261109-WA0001.jpg`, deletion staging file `files/.trash/1c485df9-2086-456b-b9d3-cd197b01a777`, and FTS table `message_ftsv2_content`) and unified timeline correlation in `dumps/for_hai/`.

---

## 2. Completed Findings by Le Viet Cuong (`20235586`)
1. **Static Backup Security Audit (`results/allowbackup_audit.txt`):**
   - `com.whatsapp` v2.26.44.71 sets `android:allowBackup="false"` and declares `com.whatsapp.backup.google.GoogleBackupAgent`, causing unrooted `adb backup` to return a 47-byte empty header.
2. **SHA-256 Chain of Custody (`results/hash_table.csv`):**
   - Logged and verified `31` raw evidence files across `dumps/whatsapp/`, `dumps/for_huy/`, `dumps/for_linh/`, and `dumps/for_hai/`.
   - Core database hashes:
     - `msgstore.db` (`2,789,376` B): `85BD6B0411FB74753899F45E71976F2A34618EA0032BF4FB042AB4ED49672B57`
     - `msgstore.db-wal` (`465,592` B): `E77A9F0B21847170BD4836BF099DF381F0E7E1210A0BCADDCC5BBB47AFC94589`
     - `wa.db` (`1,036,288` B): `C30CBABC1040DC73D4FD0F7FF9EEBA84BBE5A2671D4682E49D6A91D0A5B7B85B`
     - `files/key` (`158` B): `328867704B7B09EA2F53DE99EF59A2B87D7AB0B8EEED25E2DF4F26BE9F46B0B2`
3. **Active Relational Reconstruction (`results/reconstruction_logs/whatsapp/`):**
   - `wa_contacts.csv`: Reconstructed `2` active contact entries from `wa.db` (including modern privacy Linked Identifier `178774524043344@lid`).
   - `wa_messages.csv`: Reconstructed `5` active messages (`msg_id = 1..5`, including Vietnamese UTF-8 text and image attachment `Media/WhatsApp Images/Sent/IMG-20261109-WA0001.jpg`). Observed sequence gap at `msg_id = 6` (handed off to Linh for WAL recovery).
   - `wa_calls.csv`: Reconstructed `2` active WhatsApp calls (`call_id = 1, 3`). Observed sequence gaps at `call_id = 2, 4` (handed off to Linh for WAL/freeblock recovery).
