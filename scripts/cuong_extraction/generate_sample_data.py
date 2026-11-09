#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sanitized Sample Dataset Generator (Role 1 - Le Viet Cuong 20235586)
Generates synthetic, realistic SQLite databases matching the schemas of:
  1. sample_data/whatsapp/wa.db        (wa_contacts)
  2. sample_data/whatsapp/msgstore.db  (jid, chat, message, message_media, call_log)
  3. sample_data/telephony/mmssms.db   (sms table for header/recovery verification)
  4. sample_data/telephony/calllog.db  (calls table for header/recovery verification)

These sanitized databases allow every team member and the course instructor to verify
all reconstruction and inspection scripts (including inside Docker) without exposing
private phone numbers or requiring live SIM cards.
"""
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2] / "sample_data"


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
        ("178774524043344@lid", None, "You (Linked ID Self-Chat)", "AVD Lab User", "Available", 1794213000000, 1),
        ("84901234567@s.whatsapp.net", "+84901234567", "Partner Lab A", "Alice Forensics", "In Lab", 1794213000000, 1),
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
    conn.execute("INSERT INTO jid (_id, raw_string) VALUES (1, '178774524043344@lid')")
    conn.execute("INSERT INTO jid (_id, raw_string) VALUES (2, '84901234567@s.whatsapp.net')")
    conn.execute("INSERT INTO chat (_id, jid_row_id) VALUES (1, 1)")

    messages = [
        (1, 1, None, 1, 1794213830014, 0, "Hello Forensic Test 01 - Normal message", 4),
        (2, 1, None, 1, 1794213987181, 0, "Xin chào Việt Nam! Thử nghiệm tiếng Việt có dấu 🚀🔍", 4),
        (3, 1, None, 1, 1794214266752, 1, "Evidence Photo Test 03", 4),
    ]
    conn.executemany(
        "INSERT INTO message (_id, chat_row_id, sender_jid_row_id, from_me, timestamp, message_type, text_data, status) VALUES (?,?,?,?,?,?,?,?)",
        messages,
    )
    conn.execute(
        "INSERT INTO message_media (message_row_id, file_path, mime_type, file_size) VALUES (3, 'Media/WhatsApp Images/Sent/IMG-20261109-WA0001.jpg', 'image/jpeg', 22488)"
    )
    conn.execute(
        "INSERT INTO call_log (_id, jid_row_id, from_me, timestamp, video_call, duration, call_result) VALUES (1, 2, 1, 1794213600000, 0, 65, 5)"
    )
    conn.execute(
        "INSERT INTO call_log (_id, jid_row_id, from_me, timestamp, video_call, duration, call_result) VALUES (3, 2, 1, 1794214000000, 1, 210, 5)"
    )
    conn.commit()
    conn.close()


def create_telephony_samples(tel_dir: Path):
    tel_dir.mkdir(parents=True, exist_ok=True)
    mmssms_db = tel_dir / "mmssms.db"
    calllog_db = tel_dir / "calllog.db"
    for p in (mmssms_db, calllog_db):
        if p.exists():
            p.unlink()

    conn = sqlite3.connect(mmssms_db)
    conn.execute("PRAGMA journal_mode=DELETE;")
    conn.execute("PRAGMA secure_delete=OFF;")
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
            ("+84901234567", 1794213000000 + i * 1000, f"DIFO_SMS_0{i}: Controlled SMS test payload #{i}"),
        )
    conn.commit()
    conn.execute("DELETE FROM sms WHERE _id IN (3, 5);")
    conn.commit()
    conn.close()

    conn = sqlite3.connect(calllog_db)
    conn.execute("PRAGMA journal_mode=DELETE;")
    conn.execute("PRAGMA secure_delete=OFF;")
    conn.execute("""
        CREATE TABLE calls (
            _id INTEGER PRIMARY KEY AUTOINCREMENT,
            number TEXT,
            date INTEGER,
            duration INTEGER,
            type INTEGER,
            name TEXT
        )
    """)
    conn.executemany(
        "INSERT INTO calls (_id, number, date, duration, type, name) VALUES (?,?,?,?,?,?)",
        [
            (1, "+84901234567", 1794213150000, 48, 2, "Partner Lab A"),
            (2, "+84909888777", 1794213350000, 95, 1, "Suspect Contact B (DELETED)"),
            (3, "+84901234567", 1794213500000, 120, 1, "Partner Lab A"),
        ],
    )
    conn.commit()
    conn.execute("DELETE FROM calls WHERE _id = 2;")
    conn.commit()
    conn.close()


def main():
    create_whatsapp_samples(BASE_DIR / "whatsapp")
    create_telephony_samples(BASE_DIR / "telephony")
    print(f"[+] Sanitized sample SQLite databases created under {BASE_DIR}")


if __name__ == "__main__":
    main()
