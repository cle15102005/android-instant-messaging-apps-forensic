#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sanitized Sample Dataset Generator (Task 1 & Integration - Cuong)
Generates synthetic, realistic SQLite databases matching the schemas of:
  1. sample_data/whatsapp/wa.db        (wa_contacts)
  2. sample_data/whatsapp/msgstore.db  (jid, chat, message, message_media, call_log)
  3. sample_data/telegram/cache4.db    (users, messages_v2 with real TL Layer 233 binary blobs)
  4. sample_data/telephony/mmssms.db   (sms table for header/recovery verification)

These sanitized databases allow every team member and the course instructor to verify
all reconstruction and inspection scripts (including inside Docker) without exposing
private phone numbers or requiring live SIM cards.
"""
import sqlite3
import struct
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2] / "sample_data"


def encode_tl_string(s: str) -> bytes:
    raw = s.encode("utf-8")
    n = len(raw)
    if n < 254:
        hdr = bytes([n])
    else:
        hdr = bytes([254, n & 0xFF, (n >> 8) & 0xFF, (n >> 16) & 0xFF])
    total = len(hdr) + n
    pad = (4 - (total % 4)) % 4
    return hdr + raw + (b"\x00" * pad)


def build_tl_message_blob(constructor_u32: int, msg_id: int, peer_id: int, date_sec: int, text: str) -> bytes:
    """Builds a 4-byte-aligned TL binary blob starting with a 32-bit constructor ID."""
    header = struct.pack("<IIiii", constructor_u32, 0x00000100, msg_id, peer_id, date_sec)
    return header + encode_tl_string(text)


def create_whatsapp_samples(wa_dir: Path):
    wa_dir.mkdir(parents=True, exist_ok=True)
    wa_db = wa_dir / "wa.db"
    msgstore_db = wa_dir / "msgstore.db"
    for p in (wa_db, msgstore_db):
        if p.exists():
            p.unlink()

    # 1. wa.db
    conn = sqlite3.connect(wa_db)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("""
        CREATE TABLE wa_contacts (
            _id INTEGER PRIMARY KEY AUTOINCREMENT,
            jid TEXT NOT NULL,
            number TEXT,
            display_name TEXT,
            wa_name TEXT,
            status TEXT,
            status_timestamp INTEGER,
            is_whatsapp_user INTEGER
        )
    """)
    contacts = [
        ("84900000001@s.whatsapp.net", "+84900000001", "Partner Account A", "Alice Forensics", "Available", 1793692800000, 1),
        ("84900000002@s.whatsapp.net", "+84900000002", "AVD Account B", "Bob AVD", "In Lab", 1793692800000, 1),
    ]
    conn.executemany(
        "INSERT INTO wa_contacts (jid, number, display_name, wa_name, status, status_timestamp, is_whatsapp_user) VALUES (?,?,?,?,?,?,?)",
        contacts,
    )
    conn.commit()
    conn.close()

    # 2. msgstore.db (modern schema: jid + chat + message + message_media + call_log)
    conn = sqlite3.connect(msgstore_db)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.executescript("""
        CREATE TABLE jid (
            _id INTEGER PRIMARY KEY AUTOINCREMENT,
            raw_string TEXT NOT NULL
        );
        CREATE TABLE chat (
            _id INTEGER PRIMARY KEY AUTOINCREMENT,
            jid_row_id INTEGER NOT NULL
        );
        CREATE TABLE message (
            _id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_row_id INTEGER NOT NULL,
            sender_jid_row_id INTEGER,
            from_me INTEGER NOT NULL,
            timestamp INTEGER NOT NULL,
            message_type INTEGER NOT NULL,
            text_data TEXT,
            status INTEGER
        );
        CREATE TABLE message_media (
            message_row_id INTEGER PRIMARY KEY,
            file_path TEXT,
            mime_type TEXT,
            file_size INTEGER
        );
        CREATE TABLE call_log (
            _id INTEGER PRIMARY KEY AUTOINCREMENT,
            jid_row_id INTEGER NOT NULL,
            from_me INTEGER NOT NULL,
            timestamp INTEGER NOT NULL,
            video_call INTEGER NOT NULL,
            duration INTEGER NOT NULL,
            call_result INTEGER NOT NULL
        );
    """)
    conn.execute("INSERT INTO jid (_id, raw_string) VALUES (1, '84900000001@s.whatsapp.net')")
    conn.execute("INSERT INTO jid (_id, raw_string) VALUES (2, '84900000002@s.whatsapp.net')")
    conn.execute("INSERT INTO chat (_id, jid_row_id) VALUES (1, 1)")

    messages = [
        (1, 1, 1, 0, 1793692800000, 0, "DIFO_WA_MSG_01: Hello from partner", 0),
        (2, 1, 2, 1, 1793692920000, 0, "DIFO_WA_MSG_02: Reply from AVD", 13),
        (3, 1, 1, 0, 1793693100000, 1, "DIFO_WA_IMG_01 caption", 0),
        (4, 1, 1, 0, 1793693520000, 15, None, 0),  # Type 15 = Revoked / Delete for Everyone tombstone
    ]
    conn.executemany(
        "INSERT INTO message (_id, chat_row_id, sender_jid_row_id, from_me, timestamp, message_type, text_data, status) VALUES (?,?,?,?,?,?,?,?)",
        messages,
    )
    conn.execute(
        "INSERT INTO message_media (message_row_id, file_path, mime_type, file_size) VALUES (3, 'Media/WhatsApp Images/IMG-20261103-WA0001.jpg', 'image/jpeg', 145920)"
    )
    conn.execute(
        "INSERT INTO call_log (_id, jid_row_id, from_me, timestamp, video_call, duration, call_result) VALUES (1, 1, 0, 1793693280000, 0, 30, 5)"
    )
    conn.commit()
    conn.close()


def create_telegram_samples(tg_dir: Path):
    tg_dir.mkdir(parents=True, exist_ok=True)
    cache4_db = tg_dir / "cache4.db"
    if cache4_db.exists():
        cache4_db.unlink()

    conn = sqlite3.connect(cache4_db)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.executescript("""
        CREATE TABLE users (
            uid INTEGER PRIMARY KEY,
            name TEXT,
            status INTEGER,
            data BLOB
        );
        CREATE TABLE messages_v2 (
            mid INTEGER PRIMARY KEY,
            uid INTEGER,
            read_state INTEGER,
            send_state INTEGER,
            date INTEGER,
            data BLOB,
            out INTEGER,
            ttl INTEGER,
            media INTEGER
        );
    """)

    user_blob_1 = struct.pack("<I", 0x215C4438) + encode_tl_string("Alice") + encode_tl_string("84900000001")
    user_blob_2 = struct.pack("<I", 0x215C4438) + encode_tl_string("Bob_AVD") + encode_tl_string("84900000002")
    conn.execute("INSERT INTO users (uid, name, status, data) VALUES (?, ?, ?, ?)", (10001, "Alice;;;alice_forensics", 1, user_blob_1))
    conn.execute("INSERT INTO users (uid, name, status, data) VALUES (?, ?, ?, ?)", (10002, "Bob AVD;;;bob_difo", 1, user_blob_2))

    # TL_message constructor + 4-byte-aligned TL string
    msg1_blob = build_tl_message_blob(0x38116EE0, 1, 10001, 1793694000, "DIFO_TG_MSG_01: Telegram test message")
    msg2_blob = build_tl_message_blob(0x38116EE0, 2, 10001, 1793694120, "DIFO_TG_IMG_01.jpg")
    # Service message (PhoneCall) without text string
    msg3_blob = struct.pack("<IIII", 0x9E19A1F6, 0x00000004, 3, 1793694300)

    conn.execute(
        "INSERT INTO messages_v2 (mid, uid, read_state, send_state, date, data, out, ttl, media) VALUES (?,?,?,?,?,?,?,?,?)",
        (1, 10001, 3, 0, 1793694000, msg1_blob, 0, 0, 0),
    )
    conn.execute(
        "INSERT INTO messages_v2 (mid, uid, read_state, send_state, date, data, out, ttl, media) VALUES (?,?,?,?,?,?,?,?,?)",
        (2, 10001, 3, 0, 1793694120, msg2_blob, 1, 0, 1),
    )
    conn.execute(
        "INSERT INTO messages_v2 (mid, uid, read_state, send_state, date, data, out, ttl, media) VALUES (?,?,?,?,?,?,?,?,?)",
        (3, 10001, 3, 0, 1793694300, msg3_blob, 0, 0, 0),
    )
    conn.commit()
    conn.close()


def create_telephony_samples(tel_dir: Path):
    tel_dir.mkdir(parents=True, exist_ok=True)
    mmssms_db = tel_dir / "mmssms.db"
    if mmssms_db.exists():
        mmssms_db.unlink()

    conn = sqlite3.connect(mmssms_db)
    conn.execute("PRAGMA journal_mode=DELETE;")
    conn.execute("""
        CREATE TABLE sms (
            _id INTEGER PRIMARY KEY AUTOINCREMENT,
            address TEXT,
            date INTEGER,
            read INTEGER,
            type INTEGER,
            body TEXT
        )
    """)
    for i in range(1, 6):
        conn.execute(
            "INSERT INTO sms (address, date, read, type, body) VALUES (?, ?, 1, 1, ?)",
            ("+84900000001", 1793696400000 + i * 1000, f"DIFO_SMS_0{i}: Controlled SMS test payload #{i}"),
        )
    conn.commit()
    conn.close()


def main():
    create_whatsapp_samples(BASE_DIR / "whatsapp")
    create_telegram_samples(BASE_DIR / "telegram")
    create_telephony_samples(BASE_DIR / "telephony")
    print(f"[+] Sanitized sample SQLite databases created under {BASE_DIR}")


if __name__ == "__main__":
    main()
