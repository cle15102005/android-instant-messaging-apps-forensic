#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WhatsApp Active Database Reconstruction Script (Role 1 - Le Viet Cuong 20235586)
================================================================================
Reconstructs active Contacts (from `wa.db`), active Chat History (from `msgstore.db`),
and active Call Logs (from `msgstore.db` / `wa_calllog_dummy.db`) without modifying
original evidence files (100% SHA-256 preserved).

Note on Scope Boundary:
- This script reconstructs ONLY the active (WAL-merged) database state (`wa_contacts.csv`,
  `wa_messages.csv`, `wa_calls.csv`).
- Recovery of deleted records from uncheckpointed `.db-wal` frames (`msg_id = 6`,
  `call_id = 2`) and post-checkpoint B-Tree freeblocks (`call_id = 4`, Android SMS/Call
  Logs) is delegated to Role 3 (Nguyen Ngoc Linh - `scripts/linh_recovery/`).

Usage:
    python scripts/cuong_extraction/whatsapp_reconstruct.py --dump-dir ./dumps/whatsapp --out-dir ./results/reconstruction_logs/whatsapp
"""
import argparse
import csv
import hashlib
import shutil
import sqlite3
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@contextmanager
def connect_wal_merged_temp(db_path: Path):
    """
    Copies .db, .db-wal, and .db-shm into an isolated temporary directory so SQLite
    can read the active WAL-merged state without modifying a single byte of original evidence.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        for suffix in ("", "-wal", "-shm", "-journal"):
            candidate = db_path.parent / f"{db_path.name}{suffix}"
            if candidate.exists():
                shutil.copy2(candidate, tmp_path / candidate.name)
        conn = sqlite3.connect(tmp_path / db_path.name)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()


def ms_to_iso(ts_ms) -> str:
    if not ts_ms or ts_ms <= 0:
        return ""
    try:
        return datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return str(ts_ms)


def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None


def reconstruct_contacts(wa_db: Path, out_csv: Path) -> int:
    if not wa_db.exists():
        print(f"[-] {wa_db} not found, skipping contacts reconstruction.")
        return 0

    rows_out = []
    with connect_wal_merged_temp(wa_db) as conn:
        if table_exists(conn, "wa_contacts"):
            cols = [r["name"] for r in conn.execute("PRAGMA table_info(wa_contacts)").fetchall()]
            select_cols = [
                c for c in ("jid", "number", "display_name", "wa_name", "status", "status_timestamp", "is_whatsapp_user")
                if c in cols
            ]
            query = f"SELECT {', '.join(select_cols)} FROM wa_contacts ORDER BY jid"
            for r in conn.execute(query):
                d = dict(r)
                if "status_timestamp" in d:
                    d["status_timestamp_utc"] = ms_to_iso(d["status_timestamp"])
                rows_out.append(d)

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    if rows_out:
        with out_csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows_out[0].keys()))
            writer.writeheader()
            writer.writerows(rows_out)
    print(f"[+] Active contacts reconstructed: {len(rows_out)} -> {out_csv}")
    return len(rows_out)


def _fetch_messages_from_conn(conn: sqlite3.Connection) -> dict:
    """Returns dict mapping msg_id -> row dict from active tables."""
    results = {}
    if table_exists(conn, "message") and table_exists(conn, "chat") and table_exists(conn, "jid"):
        has_media = table_exists(conn, "message_media")
        media_join = "LEFT JOIN message_media mm ON mm.message_row_id = m._id" if has_media else ""
        media_cols = ", mm.file_path AS media_file_path, mm.mime_type AS media_mime_type, mm.file_size AS media_size" if has_media else ""
        query = f"""
            SELECT
                m._id AS msg_id,
                chat_jid.raw_string AS chat_jid,
                sender_jid.raw_string AS sender_jid,
                m.from_me,
                m.timestamp,
                m.message_type,
                m.text_data,
                m.status
                {media_cols}
            FROM message m
            LEFT JOIN chat c ON m.chat_row_id = c._id
            LEFT JOIN jid chat_jid ON c.jid_row_id = chat_jid._id
            LEFT JOIN jid sender_jid ON m.sender_jid_row_id = sender_jid._id
            {media_join}
            ORDER BY m.timestamp ASC, m._id ASC
        """
        for r in conn.execute(query):
            d = dict(r)
            d["timestamp_utc"] = ms_to_iso(d.get("timestamp"))
            d["direction"] = "OUTGOING" if d.get("from_me") == 1 else "INCOMING"
            mtype = d.get("message_type")
            if mtype in (15, 64):
                d["forensic_note"] = "REVOKED_OR_DELETED_TOMBSTONE"
            elif mtype == 1:
                d["forensic_note"] = "IMAGE"
            elif mtype == 0:
                d["forensic_note"] = "TEXT"
            else:
                d["forensic_note"] = f"TYPE_{mtype}"
            results[d["msg_id"]] = d
    return results


def reconstruct_messages(msgstore_db: Path, out_csv: Path) -> int:
    with connect_wal_merged_temp(msgstore_db) as wal_conn:
        active_msgs = _fetch_messages_from_conn(wal_conn)

    rows_out = [active_msgs[k] for k in sorted(active_msgs.keys())]
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    if rows_out:
        with out_csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows_out[0].keys()))
            writer.writeheader()
            writer.writerows(rows_out)
    print(f"[+] Active messages reconstructed: {len(rows_out)} -> {out_csv}")
    return len(rows_out)


def _fetch_calls_from_db(db_path: Path) -> list:
    rows_out = []
    if not db_path.exists():
        return rows_out
    with connect_wal_merged_temp(db_path) as conn:
        if table_exists(conn, "call_log") and table_exists(conn, "jid"):
            query = """
                SELECT
                    cl._id AS call_id,
                    j.raw_string AS peer_jid,
                    cl.from_me,
                    cl.timestamp,
                    cl.video_call,
                    cl.duration,
                    cl.call_result
                FROM call_log cl
                LEFT JOIN jid j ON cl.jid_row_id = j._id
                ORDER BY cl.timestamp ASC
            """
            for r in conn.execute(query):
                d = dict(r)
                d["timestamp_utc"] = ms_to_iso(d.get("timestamp"))
                d["direction"] = "OUTGOING" if d.get("from_me") == 1 else "INCOMING"
                rows_out.append(d)
    return rows_out


def reconstruct_calls(msgstore_db: Path, out_csv: Path) -> int:
    rows_out = _fetch_calls_from_db(msgstore_db)
    if not rows_out:
        dummy_call_db = msgstore_db.parent / "wa_calllog_dummy.db"
        rows_out = _fetch_calls_from_db(dummy_call_db)

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    if rows_out:
        with out_csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows_out[0].keys()))
            writer.writeheader()
            writer.writerows(rows_out)
    print(f"[+] Active calls reconstructed: {len(rows_out)} -> {out_csv}")
    return len(rows_out)


def main():
    parser = argparse.ArgumentParser(description="Reconstruct active WhatsApp contacts, chats, and call logs")
    parser.add_argument("--dump-dir", default="./dumps/whatsapp", help="Directory containing msgstore.db and wa.db")
    parser.add_argument("--out-dir", default="./results/reconstruction_logs/whatsapp", help="Output CSV directory")
    args = parser.parse_args()

    dump_dir = Path(args.dump_dir)
    out_dir = Path(args.out_dir)
    msgstore = dump_dir / "msgstore.db"
    wa_db = dump_dir / "wa.db"

    if not msgstore.exists():
        print(f"[-] {msgstore} not found.")
        return

    before_hash = sha256_file(msgstore)
    reconstruct_contacts(wa_db, out_dir / "wa_contacts.csv")
    reconstruct_messages(msgstore, out_dir / "wa_messages.csv")
    reconstruct_calls(msgstore, out_dir / "wa_calls.csv")
    after_hash = sha256_file(msgstore)
    assert before_hash == after_hash, "Integrity violation: msgstore.db hash changed!"
    print(f"[+] SHA-256 integrity verified (unchanged): {after_hash}")


if __name__ == "__main__":
    main()
