# Role 4 (Dinh Ha Hai - 20235589): Non-Database Artifacts, Cache & Unified Timeline Analysis

## Raw Evidence Input (Provided by Cuong in `dumps/for_hai/`)
- `com.whatsapp_datadump.tar.gz` (`29,970,736` bytes, 748 files from `/data/data/com.whatsapp/`).

## Tasks for Hai (TODO)
1. Inspect `shared_prefs/` (`com.whatsapp_preferences_light.xml`, `register_phone_prefs.xml`, `keystore.xml`, `wacrypto.xml`) to extract account registration metadata and timestamps.
2. Inspect media and cache artifacts (`Media/WhatsApp Images/Sent/IMG-20261109-WA0001.jpg`, `cache/Profile Pictures/`) and test EXIF metadata stripping using `exiftool` or Python `Pillow`.
3. Analyze the deletion staging artifact in `files/.trash/1c485df9-2086-456b-b9d3-cd197b01a777` and Full-Text Search index `message_ftsv2_content` in `msgstore.db`.
4. Correlate filesystem `mtime` timestamps with SQLite `message`/`call_log` timestamps into `results/timeline/unified_forensic_timeline.csv` and complete Section 4.4 of the LaTeX report.
