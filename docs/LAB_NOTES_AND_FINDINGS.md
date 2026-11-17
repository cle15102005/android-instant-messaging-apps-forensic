# Forensic Lab Notes & Empirical Findings (Roles 1 & 3 Completed — Ready for Roles 2 & 4)

## 1. Scope & Justification for Focusing 100% on WhatsApp (`com.whatsapp` v2.26.44.71)
- **Syllabus Prompt Interpretation:** The project topic (*"Extracting and Analyzing WhatsApp/Telegram/Zalo Chat Databases from an Android/iOS Backup, Recovering Deleted SMS/Call Logs, and Analyzing App Artifacts (Cache, SQLite Databases)"*) uses `/` to denote candidate Instant Messaging platforms and mobile OS testbeds, while *"Recovering Deleted SMS/Call Logs"* within an Instant Messaging topic refers to recovering deleted text messages (`message` table) and voice/video call logs (`call_log` table) of the IM application.
- **Empirical Anti-Emulator & Registration Findings on Android 11 AVD (`DiFo`):**
  1. **WhatsApp (`com.whatsapp` v2.26.44.71):** Successfully registered, authenticated, and generated rich forensic evidence across **18 SQLite databases** and **748 sandbox files** (`29.97 MB` compressed in `com.whatsapp_datadump.tar.gz`).
  2. **Telegram (`org.telegram.messenger.web` v13.2.0):** Enforces a paid "One-time SMS Fee (₫18,750)" via Google Play billing for new Vietnamese (`+84`) phone numbers on virtualized devices.
  3. **Zalo (`com.zing.zalo` v26.10.02):** Blocks account registration/login on x86_64 Android emulators with hardware attestation error `(2028): Unable to create a new account on this device`.
- **4-Member Deep-Dive Workload on WhatsApp:**
  - **Role 1 — Le Viet Cuong (`20235586`) [COMPLETED (100%)]:** Testbed setup (`DiFo` AVD), static `allowBackup` audit, live WhatsApp chat/media/call/deletion acquisition with SHA-256 chain of custody (`results/hash_table.csv`), and active relational reconstruction (`wa_contacts.csv`, `wa_messages.csv`, `wa_calls.csv`).
  - **Role 2 — Hoang Quoc Huy (`20235594`) [PENDING MEMBER EXECUTION]:** Signal Protocol E2EE database analysis (`axolotl.db` containing `1,624` prekeys, `identities`, `signed_prekeys`), `files/key` (`158 bytes`) structure for `.crypt14/.crypt15`, and auxiliary WhatsApp SQLite databases (`status.db`, `stickers.db`, `chatsettings.db`, `companion_devices.db`, `media.db`, `sync.db`) in `dumps/for_huy/`.
  - **Role 3 — Nguyen Ngoc Linh (`20235599`) [COMPLETED (100%)]:** Pre-checkpoint SQLite WAL recovery (deleted WhatsApp text message `msg_id = 6` in `msgstore.db-wal` and deleted WhatsApp voice call `call_id = 2` in `wa_calllog_dummy.db-wal`) and post-checkpoint B-Tree leaf page carving (deleted WhatsApp missed call `call_id = 4` at Page 4, offset `3811`, file offset `16099` in `wa_calllog_dummy.db`).
  - **Role 4 — Dinh Ha Hai (`20235589`) [PENDING MEMBER EXECUTION]:** Non-database WhatsApp artifacts (`shared_prefs/*.xml`, `cache/Profile Pictures/`, EXIF stripping on `IMG-20261109-WA0001.jpg`, deletion staging file `files/.trash/1c485df9-2086-456b-b9d3-cd197b01a777`, and FTS table `message_ftsv2_content`) and unified timeline correlation in `dumps/for_hai/`.

---

## 2. Completed Findings by Le Viet Cuong (`20235586` — Role 1)
1. **Static Backup Security Audit (`results/allowbackup_audit.txt`):**
   - `com.whatsapp` v2.26.44.71 sets `android:allowBackup="false"` and declares `com.whatsapp.backup.google.GoogleBackupAgent`, causing unrooted `adb backup` to return a 47-byte empty header.
2. **SHA-256 Chain of Custody (`results/hash_table.csv`):**
   - Logged and verified `29` raw WhatsApp evidence files across `dumps/whatsapp/`, `dumps/for_huy/`, `dumps/for_linh/`, and `dumps/for_hai/`.
3. **Active Relational Reconstruction (`results/reconstruction_logs/whatsapp/`):**
   - `wa_contacts.csv`: Reconstructed `2` active contact entries from `wa.db`.
   - `wa_messages.csv`: Reconstructed `5` active messages (`msg_id = 1..5`, including Vietnamese UTF-8 text and image attachment `Media/WhatsApp Images/Sent/IMG-20261109-WA0001.jpg`). Observed sequence gap at `msg_id = 6` (handed off to Linh).
   - `wa_calls.csv`: Reconstructed `2` active WhatsApp calls (`call_id = 1, 3`). Observed sequence gaps at `call_id = 2, 4` (handed off to Linh).

---

## 3. Completed Findings by Nguyen Ngoc Linh (`20235599` — Role 3)
1. **SQLite Header & WAL Frame Inspection (`sqlite_header_check.py` & `recover_deleted_records.py`):**
   - Verified `page_size = 4096` bytes and WAL journal mode (`write_version = 2`, `read_version = 2`) on both `msgstore.db` and `wa_calllog_dummy.db`.
   - Parsed `msgstore.db-wal` (`465,592` B): `113` frames across `33` distinct pages; `message` root page (`Page 98`) modified in frames `21, 60, 75, 98` and committed at frame `113`.
   - Parsed `wa_calllog_dummy.db-wal` (`4,152` B): `1` frame modifying `call_log` root page (`Page 4`) and committed at frame `1`.
2. **Pre-Checkpoint WAL Recovery (`TC1` — Immutable Main DB vs. WAL-Merged Snapshot):**
   - Recovered `message._id = 6` (`text_data = "Delete this temporary access code: 849201"`, `key_id = "ACDBDBF6A66CAD14468E248005ECA3CB"`, `timestamp = 1794214023112`) from `msgstore.db` (`?mode=ro&immutable=1`), confirming its absence in the WAL-merged read-only snapshot.
   - Recovered `call_log._id = 2` (`call_id = "WA_CALL_DEL_WAL_02"`, `from_me = 0`, `duration = 142s`, `bytes_transferred = 894120`, `timestamp = 1794213800000`) from `wa_calllog_dummy.db` (`?mode=ro&immutable=1`), confirming its absence in the WAL-merged snapshot.
3. **Post-Checkpoint B-Tree Table Leaf Carving (`TC2` — Unallocated Page Space):**
   - Implemented a custom Varint and 21-column Serial-Type decoder for SQLite B-Tree table leaf pages (`page_type = 0x0D`).
   - On `Page 4` of `wa_calllog_dummy.db` (`cell_count = 3`, `pointer_array_end = 14`, `cell_content_start = 3885`, `freeblock_head = 0`), located and decoded the surviving 74-byte cell (`72-byte` payload) of `call_log._id = 4` (`call_id = "WA_CALL_DEL_FREEBLOCK_04"`, `from_me = 0`, `duration = 0s`, `call_result = 2`, `bytes_transferred = 12400`, `peer_jid = "84909888777@s.whatsapp.net"`) at **page offset `3811`** (file offset `16,099`) inside `unallocated_page_space`.
   - Documented the `wa_calllog_dummy.db-wal` revalidation SHA-256 (`EEC6E981...`) in `results/hash_table.csv` without altering the original acquisition entry (`AD8A38EF...`).
