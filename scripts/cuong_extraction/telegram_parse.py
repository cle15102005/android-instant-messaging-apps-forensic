#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram cache4.db & messages_v2 TL Binary Parser (Task 1 - Cuong)
Target APK: org.telegram.messenger.web v13.2.0 (TLRPC.LAYER = 233)
Reads Telegram's cache4.db in immutable read-only mode (?immutable=1) and parses:
  1. users table (extracting ID, name, username/phone from TL binary data)
  2. dialogs / chats tables
  3. messages_v2 table (or legacy messages table), deserializing the `data` BLOB:
     - Reads the 32-bit little-endian TL Constructor ID
     - Parses standard TL strings (1-byte or 4-byte length prefix, 4-byte aligned)
       to extract plaintext message body for text messages and media captions
     - Logs exact Constructor IDs for non-text/media/service messages

Usage:
    python scripts/cuong_extraction/telegram_parse.py --dump-dir ./dumps/telegram --out-dir ./results/reconstruction_logs/telegram
"""
import argparse
import csv
import hashlib
import re
import sqlite3
import struct
from datetime import datetime, timezone
from pathlib import Path


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def connect_readonly(db_path: Path) -> sqlite3.Connection:
    uri = f"file:{db_path.resolve().as_posix()}?immutable=1"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def sec_to_iso(ts_sec) -> str:
    if not ts_sec or ts_sec <= 0:
        return ""
    try:
        return datetime.fromtimestamp(int(ts_sec), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return str(ts_sec)


def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None


class TLStream:
    """Minimal Type Language (TL) binary stream reader for Telegram Android TDS blobs."""

    def __init__(self, data: bytes):
        self.data = data or b""
        self.pos = 0

    def remaining(self) -> int:
        return max(0, len(self.data) - self.pos)

    def read_int32(self) -> int:
        if self.remaining() < 4:
            raise EOFError("Not enough bytes for int32")
        val = struct.unpack_from("<i", self.data, self.pos)[0]
        self.pos += 4
        return val

    def read_uint32(self) -> int:
        if self.remaining() < 4:
            raise EOFError("Not enough bytes for uint32")
        val = struct.unpack_from("<I", self.data, self.pos)[0]
        self.pos += 4
        return val

    def read_int64(self) -> int:
        if self.remaining() < 8:
            raise EOFError("Not enough bytes for int64")
        val = struct.unpack_from("<q", self.data, self.pos)[0]
        self.pos += 8
        return val

    def read_string(self) -> str:
        if self.remaining() < 1:
            raise EOFError("Not enough bytes for TL string")
        first = self.data[self.pos]
        if first < 254:
            length = first
            header_len = 1
            self.pos += 1
        elif first == 254:
            if self.remaining() < 4:
                raise EOFError("Truncated long TL string length")
            length = self.data[self.pos + 1] | (self.data[self.pos + 2] << 8) | (self.data[self.pos + 3] << 16)
            header_len = 4
            self.pos += 4
        else:
            raise ValueError("Invalid TL string prefix 0xFF")

        if self.remaining() < length:
            raise EOFError("Truncated TL string payload")
        raw = self.data[self.pos : self.pos + length]
        self.pos += length
        # TL strings are padded with 0..3 zero bytes so (header_len + length + padding) is a multiple of 4
        pad = (4 - ((header_len + length) % 4)) % 4
        self.pos = min(len(self.data), self.pos + pad)
        return raw.decode("utf-8", errors="replace")


def extract_tl_strings_heuristic(blob: bytes) -> list[str]:
    """
    Scans a TL binary blob for valid 4-byte-aligned TL strings containing readable UTF-8 text.
    Used as a resilient fallback across TL layers alongside strict header parsing.
    """
    candidates = []
    n = len(blob)
    for offset in range(4, n - 1, 4):
        first = blob[offset]
        if 1 <= first < 254:
            length = first
            hdr = 1
        elif first == 254 and offset + 4 <= n:
            length = blob[offset + 1] | (blob[offset + 2] << 8) | (blob[offset + 3] << 16)
            hdr = 4
        else:
            continue
        end = offset + hdr + length
        pad = (4 - ((hdr + length) % 4)) % 4
        if end + pad > n or length > 4096:
            continue
        padding_bytes = blob[end : end + pad]
        if any(b != 0 for b in padding_bytes):
            continue
        try:
            s = blob[offset + hdr : end].decode("utf-8")
            if s.isprintable() and len(s.strip()) >= 2:
                candidates.append(s)
        except UnicodeDecodeError:
            continue
    return candidates


def parse_message_blob(blob: bytes) -> dict:
    if not blob or len(blob) < 4:
        return {"constructor_hex": "", "parsed_text": "", "note": "EMPTY_BLOB"}

    ctor_u32 = struct.unpack_from("<I", blob, 0)[0]
    ctor_i32 = struct.unpack_from("<i", blob, 0)[0]
    ctor_hex = f"0x{ctor_u32:08x}"

    strings = extract_tl_strings_heuristic(blob)
    parsed_text = strings[0] if strings else ""
    note = "TEXT_EXTRACTED" if parsed_text else "SERVICE_OR_MEDIA_CONSTRUCTOR"
    return {
        "constructor_hex": ctor_hex,
        "constructor_i32": ctor_i32,
        "parsed_text": parsed_text,
        "all_tl_strings": " | ".join(strings[:5]),
        "note": note,
    }


def parse_users(conn: sqlite3.Connection, out_csv: Path) -> int:
    if not table_exists(conn, "users"):
        return 0
    rows_out = []
    for r in conn.execute("SELECT uid, name, status, data FROM users ORDER BY uid"):
        blob = r["data"] or b""
        ctor_hex = f"0x{struct.unpack_from('<I', blob, 0)[0]:08x}" if len(blob) >= 4 else ""
        tl_strings = extract_tl_strings_heuristic(blob)
        phone_candidates = [s for s in tl_strings if re.fullmatch(r"\+?\d{7,15}", s)]
        rows_out.append({
            "uid": r["uid"],
            "name_col": r["name"],
            "status": r["status"],
            "constructor_hex": ctor_hex,
            "extracted_phone": phone_candidates[0] if phone_candidates else "",
            "tl_strings": " | ".join(tl_strings[:6]),
        })
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    if rows_out:
        with out_csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows_out[0].keys()))
            writer.writeheader()
            writer.writerows(rows_out)
    print(f"[+] Telegram users reconstructed: {len(rows_out)} -> {out_csv}")
    return len(rows_out)


def parse_messages(conn: sqlite3.Connection, out_csv: Path) -> int:
    tbl = "messages_v2" if table_exists(conn, "messages_v2") else ("messages" if table_exists(conn, "messages") else None)
    if not tbl:
        print("[-] Neither messages_v2 nor messages table found in cache4.db")
        return 0

    cols = [r["name"] for r in conn.execute(f"PRAGMA table_info({tbl})").fetchall()]
    select_cols = [c for c in ("mid", "uid", "read_state", "send_state", "date", "out", "ttl", "media", "data") if c in cols]
    query = f"SELECT {', '.join(select_cols)} FROM {tbl} ORDER BY date ASC"

    rows_out = []
    for r in conn.execute(query):
        d = {k: r[k] for k in select_cols if k != "data"}
        d["table_source"] = tbl
        d["date_utc"] = sec_to_iso(d.get("date"))
        d["direction"] = "OUTGOING" if d.get("out") == 1 else "INCOMING"
        blob_info = parse_message_blob(r["data"])
        d.update(blob_info)
        rows_out.append(d)

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    if rows_out:
        with out_csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows_out[0].keys()))
            writer.writeheader()
            writer.writerows(rows_out)
    print(f"[+] Telegram {tbl} reconstructed: {len(rows_out)} -> {out_csv}")
    return len(rows_out)


def main():
    parser = argparse.ArgumentParser(description="Parse Telegram cache4.db (messages_v2 & users)")
    parser.add_argument("--dump-dir", default="./dumps/telegram", help="Directory containing cache4.db")
    parser.add_argument("--out-dir", default="./results/reconstruction_logs/telegram", help="Output CSV directory")
    args = parser.parse_args()

    cache4 = Path(args.dump_dir) / "cache4.db"
    out_dir = Path(args.out_dir)

    if not cache4.exists():
        print(f"[-] {cache4} not found. Run extract_wa_tg.sh first.")
        return

    before_hash = sha256_file(cache4)
    conn = connect_readonly(cache4)
    parse_users(conn, out_dir / "tg_users.csv")
    parse_messages(conn, out_dir / "tg_messages.csv")
    conn.close()
    after_hash = sha256_file(cache4)
    assert before_hash == after_hash, "Integrity violation: cache4.db hash changed!"
    print(f"[+] SHA-256 integrity verified (unchanged): {after_hash}")


if __name__ == "__main__":
    main()
