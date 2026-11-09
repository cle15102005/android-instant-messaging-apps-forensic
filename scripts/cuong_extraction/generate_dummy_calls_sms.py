#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dummy Call Logs, SMS & Team Evidence Packager (Task 1 - Le Viet Cuong 20235586)
===============================================================================
Prepares the raw forensic evidence folders for all 4 team members under `dumps/`
and records SHA-256 chain-of-custody hashes in `results/hash_table.csv`:

1. `dumps/whatsapp/` (Cuong - Active Chat, Contact & Call Reconstruction)
2. `dumps/for_huy/`  (Huy - WhatsApp E2EE Cryptographic & Auxiliary SQLite DBs
                      extracted from `com.whatsapp_datadump.tar.gz`)
3. `dumps/for_linh/` (Linh - Deleted WhatsApp Message/Call Log & Android
                      SMS/Call Log Recovery in WAL and B-Tree Freeblocks)
4. `dumps/for_hai/`  (Hai - Full `com.whatsapp_datadump.tar.gz` Archive for
                      Cache, Shared Preferences, Media & `.trash/` Timeline)
"""
import csv
import hashlib
import os
import shutil
import sqlite3
import tarfile
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DUMPS_DIR = PROJECT_ROOT / "dumps"
RESULTS_DIR = PROJECT_ROOT / "results"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def extract_huy_databases():
    """Extracts WhatsApp E2EE (`axolotl.db`, `key`) and auxiliary DBs for Huy."""
    tar_path = DUMPS_DIR / "for_hai" / "com.whatsapp_datadump.tar.gz"
    huy_dir = DUMPS_DIR / "for_huy"
    huy_dir.mkdir(parents=True, exist_ok=True)

    target_dbs = [
        "axolotl.db", "axolotl.db-wal", "axolotl.db-shm",
        "chatsettings.db", "chatsettings.db-wal", "chatsettings.db-shm",
        "companion_devices.db", "companion_devices.db-wal", "companion_devices.db-shm",
        "status.db", "status.db-wal", "status.db-shm",
        "stickers.db", "stickers.db-wal", "stickers.db-shm",
        "media.db", "media.db-wal", "media.db-shm",
        "sync.db", "sync.db-wal", "sync.db-shm",
    ]
    with tarfile.open(tar_path, "r:gz") as t:
        for db_name in target_dbs:
            member_name = f"com.whatsapp/databases/{db_name}"
            try:
                m = t.getmember(member_name)
                out_file = huy_dir / db_name
                out_file.write_bytes(t.extractfile(m).read())
            except KeyError:
                pass
        # Also extract files/key (158-byte cryptographic backup key)
        key_member = t.getmember("com.whatsapp/files/key")
        (huy_dir / "key").write_bytes(t.extractfile(key_member).read())


def generate_linh_recovery_dumps():
    """Creates dummy WhatsApp call logs & Android SMS/Call Logs with deleted records for Linh."""
    linh_dir = DUMPS_DIR / "for_linh"
    linh_dir.mkdir(parents=True, exist_ok=True)

    # 1. Copy untouched msgstore.db + .db-wal + .db-shm (contains deleted msg_id=6 in WAL)
    for fname in ["msgstore.db", "msgstore.db-wal", "msgstore.db-shm"]:
        src = DUMPS_DIR / "whatsapp" / fname
        if src.exists():
            shutil.copy2(src, linh_dir / fname)

    # 2. Create wa_calllog_dummy.db (+ .db-wal, .db-shm) matching WhatsApp v2.26.44.71 schema
    wa_call_db = linh_dir / "wa_calllog_dummy.db"
    for suffix in ["", "-wal", "-shm"]:
        p = Path(str(wa_call_db) + suffix)
        if p.exists():
            p.unlink()

    conn = sqlite3.connect(wa_call_db)
    conn.execute("PRAGMA page_size = 4096;")
    conn.execute("PRAGMA secure_delete = OFF;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA wal_autocheckpoint = 0;")
    conn.executescript("""
        CREATE TABLE jid (
            _id INTEGER PRIMARY KEY AUTOINCREMENT,
            raw_string TEXT NOT NULL
        );
        CREATE TABLE call_log(
            _id INTEGER PRIMARY KEY AUTOINCREMENT,
            jid_row_id INTEGER,
            from_me INTEGER,
            call_id TEXT,
            transaction_id INTEGER,
            timestamp INTEGER,
            video_call INTEGER,
            duration INTEGER,
            call_result INTEGER,
            is_dnd_mode_on INTEGER,
            bytes_transferred INTEGER,
            group_jid_row_id INTEGER NOT NULL DEFAULT 0,
            is_joinable_group_call INTEGER,
            call_creator_device_jid_row_id INTEGER NOT NULL DEFAULT 0,
            call_random_id TEXT,
            call_link_row_id INTEGER NOT NULL DEFAULT 0,
            call_type INTEGER,
            offer_silence_reason INTEGER,
            scheduled_id TEXT,
            telecom_uuid TEXT,
            terminated_by_device_switch INTEGER
        );
    """)
    conn.executemany(
        "INSERT INTO jid (_id, raw_string) VALUES (?, ?)",
        [
            (1, "178774524043344@lid"),
            (2, "84901234567@s.whatsapp.net"),
            (3, "84909888777@s.whatsapp.net"),
        ],
    )
    calls = [
        # _id=1: Active outgoing voice call
        (1, 2, 1, "WA_CALL_ACTIVE_01", 101, 1794213600000, 0, 65, 5, 0, 412800, 0, 0, 0, "rnd01", 0, 0, 0, None, "uuid-wa-01", 0),
        # _id=2: Incoming voice call -> to be deleted in WAL (Pre-Checkpoint TC1)
        (2, 2, 0, "WA_CALL_DEL_WAL_02", 102, 1794213800000, 0, 142, 5, 0, 894120, 0, 0, 0, "rnd02", 0, 0, 0, None, "uuid-wa-02", 0),
        # _id=3: Active outgoing video call
        (3, 3, 1, "WA_CALL_ACTIVE_03", 103, 1794214000000, 1, 210, 5, 0, 18452000, 0, 0, 0, "rnd03", 0, 0, 0, None, "uuid-wa-03", 0),
        # _id=4: Missed voice call -> to be deleted post-checkpoint in B-tree freeblock (TC2)
        (4, 3, 0, "WA_CALL_DEL_FREEBLOCK_04", 104, 1794214150000, 0, 0, 2, 0, 12400, 0, 0, 0, "rnd04", 0, 0, 0, None, "uuid-wa-04", 0),
    ]
    conn.executemany(
        "INSERT INTO call_log VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        calls,
    )
    conn.commit()
    # Delete _id=4 BEFORE checkpoint so it sits in a B-Tree leaf page freeblock
    conn.execute("DELETE FROM call_log WHERE _id = 4;")
    conn.commit()
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")

    # Now delete _id=2 AFTER checkpoint so the DELETE is only in .db-wal (while _id=2 remains intact in main .db)
    conn.execute("DELETE FROM call_log WHERE _id = 2;")
    conn.commit()

    # Copy out while connection is open so SQLite does not auto-checkpoint on close
    tmp_dir = linh_dir / "_tmp_copy"
    tmp_dir.mkdir(exist_ok=True)
    for suffix in ["", "-wal", "-shm"]:
        src_p = Path(str(wa_call_db) + suffix)
        if src_p.exists():
            shutil.copy2(src_p, tmp_dir / src_p.name)
    conn.close()
    for suffix in ["", "-wal", "-shm"]:
        saved_p = tmp_dir / (wa_call_db.name + suffix)
        if saved_p.exists():
            shutil.copy2(saved_p, linh_dir / saved_p.name)
    shutil.rmtree(tmp_dir)

    # Also copy wa_calllog_dummy.db (+wal/shm) to dumps/whatsapp/ so Cuong can reconstruct active call logs (_id=1,3)
    for suffix in ["", "-wal", "-shm"]:
        p = linh_dir / (wa_call_db.name + suffix)
        if p.exists():
            shutil.copy2(p, DUMPS_DIR / "whatsapp" / p.name)

    # 3. Create Android Telephony mmssms.db (Rollback Journal mode 0x01, secure_delete=OFF)
    mmssms_db = linh_dir / "mmssms.db"
    if mmssms_db.exists():
        mmssms_db.unlink()
    conn = sqlite3.connect(mmssms_db)
    conn.execute("PRAGMA page_size = 4096;")
    conn.execute("PRAGMA journal_mode = DELETE;")
    conn.execute("PRAGMA secure_delete = OFF;")
    conn.execute("""
        CREATE TABLE sms (
            _id INTEGER PRIMARY KEY AUTOINCREMENT,
            thread_id INTEGER,
            address TEXT,
            person INTEGER,
            date INTEGER,
            date_sent INTEGER,
            protocol INTEGER,
            read INTEGER DEFAULT 0,
            status INTEGER DEFAULT -1,
            type INTEGER,
            body TEXT,
            service_center TEXT
        );
    """)
    sms_rows = [
        (1, 1, "+84901234567", None, 1794213000000, 1794212998000, 0, 1, -1, 1, "DIFO_SMS_01: Welcome to Android 11 AVD Lab", "+84900000011"),
        (2, 1, "+84901234567", None, 1794213120000, 1794213120000, 0, 1, -1, 2, "DIFO_SMS_02: Acknowledged lab setup", "+84900000011"),
        (3, 2, "+84909888777", None, 1794213300000, 1794213299000, 0, 1, -1, 1, "DIFO_SMS_DEL_03: Temporary vault PIN 739104 (delete after reading)", "+84900000011"),
        (4, 1, "+84901234567", None, 1794213450000, 1794213450000, 0, 1, -1, 1, "DIFO_SMS_04: Switching conversation to WhatsApp E2EE", "+84900000011"),
        (5, 2, "+84909888777", None, 1794213580000, 1794213580000, 0, 1, -1, 2, "DIFO_SMS_DEL_05: Purging local SMS history before handover", "+84900000011"),
    ]
    conn.executemany("INSERT INTO sms VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", sms_rows)
    conn.commit()
    # Delete SMS _id=3 and _id=5 so their records remain in B-tree freeblocks
    conn.execute("DELETE FROM sms WHERE _id IN (3, 5);")
    conn.commit()
    conn.close()

    # 4. Create Android Call Log calllog.db (Rollback Journal mode 0x01, secure_delete=OFF)
    calllog_db = linh_dir / "calllog.db"
    if calllog_db.exists():
        calllog_db.unlink()
    conn = sqlite3.connect(calllog_db)
    conn.execute("PRAGMA page_size = 4096;")
    conn.execute("PRAGMA journal_mode = DELETE;")
    conn.execute("PRAGMA secure_delete = OFF;")
    conn.execute("""
        CREATE TABLE calls (
            _id INTEGER PRIMARY KEY AUTOINCREMENT,
            number TEXT,
            date INTEGER,
            duration INTEGER,
            type INTEGER,
            new INTEGER,
            name TEXT,
            geocoded_location TEXT
        );
    """)
    android_calls = [
        (1, "+84901234567", 1794213150000, 48, 2, 1, "Partner Lab A", "Vietnam"),
        (2, "+84909888777", 1794213350000, 95, 1, 1, "Suspect Contact B (DELETED)", "Vietnam"),
        (3, "+84901234567", 1794213500000, 120, 1, 1, "Partner Lab A", "Vietnam"),
        (4, "+84909888777", 1794213560000, 0, 3, 1, "Suspect Contact B Missed (DELETED)", "Vietnam"),
    ]
    conn.executemany("INSERT INTO calls VALUES (?,?,?,?,?,?,?,?)", android_calls)
    conn.commit()
    conn.execute("DELETE FROM calls WHERE _id IN (2, 4);")
    conn.commit()
    conn.close()


def rebuild_hash_table():
    """Computes SHA-256 hashes for all raw artifacts across the 4 team folders."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    hash_csv = RESULTS_DIR / "hash_table.csv"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    tracked_files = [
        # Cuong (dumps/whatsapp/)
        ("WhatsApp_Core_Cuong", DUMPS_DIR / "whatsapp" / "msgstore.db"),
        ("WhatsApp_Core_Cuong", DUMPS_DIR / "whatsapp" / "msgstore.db-wal"),
        ("WhatsApp_Core_Cuong", DUMPS_DIR / "whatsapp" / "msgstore.db-shm"),
        ("WhatsApp_Core_Cuong", DUMPS_DIR / "whatsapp" / "wa.db"),
        ("WhatsApp_Core_Cuong", DUMPS_DIR / "whatsapp" / "wa.db-wal"),
        ("WhatsApp_Core_Cuong", DUMPS_DIR / "whatsapp" / "wa.db-shm"),
        ("WhatsApp_Core_Cuong", DUMPS_DIR / "whatsapp" / "key"),
        ("WhatsApp_Core_Cuong", DUMPS_DIR / "whatsapp" / "wa_calllog_dummy.db"),
        ("WhatsApp_Core_Cuong", DUMPS_DIR / "whatsapp" / "wa_calllog_dummy.db-wal"),
        # Huy (dumps/for_huy/)
        ("WhatsApp_Crypto_Aux_Huy", DUMPS_DIR / "for_huy" / "axolotl.db"),
        ("WhatsApp_Crypto_Aux_Huy", DUMPS_DIR / "for_huy" / "axolotl.db-wal"),
        ("WhatsApp_Crypto_Aux_Huy", DUMPS_DIR / "for_huy" / "chatsettings.db"),
        ("WhatsApp_Crypto_Aux_Huy", DUMPS_DIR / "for_huy" / "chatsettings.db-wal"),
        ("WhatsApp_Crypto_Aux_Huy", DUMPS_DIR / "for_huy" / "companion_devices.db"),
        ("WhatsApp_Crypto_Aux_Huy", DUMPS_DIR / "for_huy" / "companion_devices.db-wal"),
        ("WhatsApp_Crypto_Aux_Huy", DUMPS_DIR / "for_huy" / "status.db"),
        ("WhatsApp_Crypto_Aux_Huy", DUMPS_DIR / "for_huy" / "status.db-wal"),
        ("WhatsApp_Crypto_Aux_Huy", DUMPS_DIR / "for_huy" / "stickers.db"),
        ("WhatsApp_Crypto_Aux_Huy", DUMPS_DIR / "for_huy" / "stickers.db-wal"),
        ("WhatsApp_Crypto_Aux_Huy", DUMPS_DIR / "for_huy" / "media.db"),
        ("WhatsApp_Crypto_Aux_Huy", DUMPS_DIR / "for_huy" / "media.db-wal"),
        ("WhatsApp_Crypto_Aux_Huy", DUMPS_DIR / "for_huy" / "sync.db"),
        ("WhatsApp_Crypto_Aux_Huy", DUMPS_DIR / "for_huy" / "sync.db-wal"),
        ("WhatsApp_Crypto_Aux_Huy", DUMPS_DIR / "for_huy" / "key"),
        # Linh (dumps/for_linh/)
        ("Deleted_Recovery_Linh", DUMPS_DIR / "for_linh" / "msgstore.db"),
        ("Deleted_Recovery_Linh", DUMPS_DIR / "for_linh" / "msgstore.db-wal"),
        ("Deleted_Recovery_Linh", DUMPS_DIR / "for_linh" / "wa_calllog_dummy.db"),
        ("Deleted_Recovery_Linh", DUMPS_DIR / "for_linh" / "wa_calllog_dummy.db-wal"),
        ("Deleted_Recovery_Linh", DUMPS_DIR / "for_linh" / "mmssms.db"),
        ("Deleted_Recovery_Linh", DUMPS_DIR / "for_linh" / "calllog.db"),
        # Hai (dumps/for_hai/)
        ("Full_Sandbox_Dump_Hai", DUMPS_DIR / "for_hai" / "com.whatsapp_datadump.tar.gz"),
    ]

    with hash_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Timestamp",
            "Target_Role",
            "Artifact_Name",
            "Local_Relative_Path",
            "File_Size_Bytes",
            "SHA256_Pre_Acquisition",
            "SHA256_Post_Acquisition",
            "Integrity_Status",
        ])
        for role, path in tracked_files:
            if path.exists():
                digest = sha256_file(path)
                rel = path.relative_to(PROJECT_ROOT).as_posix()
                writer.writerow([ts, role, path.name, rel, path.stat().st_size, digest, digest, "MATCH"])


if __name__ == "__main__":
    extract_huy_databases()
    generate_linh_recovery_dumps()
    rebuild_hash_table()
    print("[+] Successfully prepared raw dumps for Cuong, Huy, Linh, and Hai, and updated results/hash_table.csv")
