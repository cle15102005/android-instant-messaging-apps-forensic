#!/usr/bin/env python3
"""Recover the three assigned WhatsApp records without modifying source evidence."""

import argparse
import csv
import hashlib
import json
import shutil
import sqlite3
import struct
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVIDENCE_DIR = ROOT / "for_linh"
DEFAULT_OUTPUT_DIR = ROOT / "results" / "carved_sms_calls"
TARGET_TEXT = b"WA_CALL_DEL_FREEBLOCK_04"
CALL_COLUMNS = (
    "_id",
    "jid_row_id",
    "from_me",
    "call_id",
    "transaction_id",
    "timestamp",
    "video_call",
    "duration",
    "call_result",
    "is_dnd_mode_on",
    "bytes_transferred",
    "group_jid_row_id",
    "is_joinable_group_call",
    "call_creator_device_jid_row_id",
    "call_random_id",
    "call_link_row_id",
    "call_type",
    "offer_silence_reason",
    "scheduled_id",
    "telecom_uuid",
    "terminated_by_device_switch",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sqlite_uri(path: Path, immutable: bool) -> str:
    return path.resolve().as_uri() + "?mode=ro" + ("&immutable=1" if immutable else "")


def open_read_only(path: Path, immutable: bool) -> sqlite3.Connection:
    connection = sqlite3.connect(sqlite_uri(path, immutable), uri=True)
    connection.execute("PRAGMA query_only = ON")
    return connection


def fetch_row(path: Path, table: str, record_id: int, immutable: bool) -> dict[str, Any] | None:
    connection = open_read_only(path, immutable)
    try:
        columns = [
            row[1]
            for row in connection.execute(f'PRAGMA table_info("{table}")')
        ]
        if not columns:
            raise RuntimeError(f"Table not found: {table} in {path.name}")
        row = connection.execute(
            f'SELECT * FROM "{table}" WHERE "_id" = ?', (record_id,)
        ).fetchone()
        return dict(zip(columns, row)) if row is not None else None
    finally:
        connection.close()


def table_root_page(path: Path, table: str) -> int:
    connection = open_read_only(path, immutable=True)
    try:
        row = connection.execute(
            "SELECT rootpage FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table,),
        ).fetchone()
        if row is None:
            raise RuntimeError(f"Table not found: {table} in {path.name}")
        return int(row[0])
    finally:
        connection.close()


def wal_summary(path: Path, target_pages: set[int] | None = None) -> dict[str, Any]:
    raw = path.read_bytes()
    if len(raw) < 32 or raw[:4] not in (b"\x37\x7f\x06\x82", b"\x37\x7f\x06\x83"):
        raise RuntimeError(f"Invalid or truncated SQLite WAL header: {path}")
    page_size = int.from_bytes(raw[8:12], "big")
    frame_size = 24 + page_size
    frame_count = (len(raw) - 32) // frame_size
    target_frames = []
    commits = []
    pages = []
    for frame_index in range(frame_count):
        offset = 32 + frame_index * frame_size
        page_number = int.from_bytes(raw[offset : offset + 4], "big")
        database_pages = int.from_bytes(raw[offset + 4 : offset + 8], "big")
        pages.append(page_number)
        if target_pages and page_number in target_pages:
            target_frames.append(frame_index + 1)
        if database_pages:
            commits.append({"frame": frame_index + 1, "database_pages": database_pages})
    return {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "page_size": page_size,
        "frame_count": frame_count,
        "trailing_bytes": (len(raw) - 32) % frame_size,
        "distinct_pages": len(set(pages)),
        "target_page_numbers": sorted(target_pages or set()),
        "target_page_frames": target_frames,
        "commits": commits,
    }


def read_varint(data: bytes, offset: int) -> tuple[int, int]:
    value = 0
    for index in range(9):
        byte = data[offset + index]
        if index == 8:
            return (value << 8) | byte, index + 1
        value = (value << 7) | (byte & 0x7F)
        if not byte & 0x80:
            return value, index + 1
    raise ValueError("Invalid SQLite varint")


def read_serial_value(data: bytes, offset: int, serial_type: int) -> tuple[Any, int]:
    if serial_type == 0:
        return None, 0
    if serial_type == 8:
        return 0, 0
    if serial_type == 9:
        return 1, 0
    if 1 <= serial_type <= 6:
        size = (1, 2, 3, 4, 6, 8)[serial_type - 1]
        return int.from_bytes(data[offset : offset + size], "big", signed=True), size
    if serial_type == 7:
        return struct.unpack(">d", data[offset : offset + 8])[0], 8
    if serial_type in (10, 11) or serial_type < 0:
        raise ValueError(f"Reserved SQLite serial type: {serial_type}")
    size = (serial_type - 12) // 2 if serial_type % 2 == 0 else (serial_type - 13) // 2
    raw = data[offset : offset + size]
    if len(raw) != size:
        raise ValueError("Truncated SQLite record value")
    if serial_type % 2 == 0:
        return raw, size
    return raw.decode("utf-8"), size


def decode_table_leaf_cell(
    page: bytes, start: int, columns: list[dict[str, Any]]
) -> dict[str, Any] | None:
    try:
        payload_size, payload_varint_size = read_varint(page, start)
        rowid, rowid_varint_size = read_varint(page, start + payload_varint_size)
        payload_start = start + payload_varint_size + rowid_varint_size
        header_size, header_varint_size = read_varint(page, payload_start)
        header_end = payload_start + header_size
        if header_end > len(page) or header_size < header_varint_size:
            return None

        serial_types = []
        cursor = payload_start + header_varint_size
        while cursor < header_end:
            serial_type, size = read_varint(page, cursor)
            serial_types.append(serial_type)
            cursor += size
        if cursor != header_end or len(serial_types) != len(columns):
            return None

        cursor = header_end
        values = []
        for serial_type in serial_types:
            value, size = read_serial_value(page, cursor, serial_type)
            values.append(value)
            cursor += size
        if cursor - payload_start != payload_size:
            return None

        record = dict(zip((column["name"] for column in columns), values))
        for column in columns:
            if column["pk"] and column["type"].strip().upper() == "INTEGER":
                record[column["name"]] = rowid
                break
        return {"rowid": rowid, "record": record, "payload_size": payload_size}
    except (IndexError, UnicodeDecodeError, ValueError, struct.error):
        return None


def carve_deleted_call(path: Path) -> dict[str, Any]:
    connection = open_read_only(path, immutable=True)
    try:
        root_page = table_root_page(path, "call_log")
        page_size = int(connection.execute("PRAGMA page_size").fetchone()[0])
        columns = [
            {"name": row[1], "type": row[2], "pk": row[5]}
            for row in connection.execute('PRAGMA table_info("call_log")')
        ]
    finally:
        connection.close()

    raw = path.read_bytes()
    page_start = (root_page - 1) * page_size
    page = raw[page_start : page_start + page_size]
    if len(page) != page_size:
        raise RuntimeError("The call_log root page is truncated")
    header_offset = 100 if root_page == 1 else 0
    if page[header_offset] != 0x0D:
        raise RuntimeError("The call_log root page is not a table leaf page")

    cell_count = int.from_bytes(page[header_offset + 3 : header_offset + 5], "big")
    cell_content_start = int.from_bytes(page[header_offset + 5 : header_offset + 7], "big")
    if cell_content_start == 0 and page_size == 65536:
        cell_content_start = 65536
    pointer_array_end = header_offset + 8 + 2 * cell_count
    freeblock_head = int.from_bytes(page[header_offset + 1 : header_offset + 3], "big")

    freeblocks = []
    seen = set()
    current = freeblock_head
    while current:
        if current in seen or current + 4 > len(page):
            raise RuntimeError("Invalid freeblock chain in call_log root page")
        seen.add(current)
        following = int.from_bytes(page[current : current + 2], "big")
        size = int.from_bytes(page[current + 2 : current + 4], "big")
        if size < 4 or current + size > len(page):
            raise RuntimeError("Invalid freeblock size in call_log root page")
        freeblocks.append({"offset": current, "size": size, "next": following})
        current = following

    sentinel_offset = page.find(TARGET_TEXT)
    if sentinel_offset < 0:
        raise RuntimeError("Expected deleted-call identifier was not found on call_log root page")
    candidates = []
    for start in range(max(0, sentinel_offset - page_size), sentinel_offset):
        decoded = decode_table_leaf_cell(page, start, columns)
        if decoded and decoded["rowid"] == 4 and decoded["record"].get("call_id") == TARGET_TEXT.decode():
            candidates.append((start, decoded))
    if len(candidates) != 1:
        raise RuntimeError(f"Expected one valid deleted-call cell, found {len(candidates)}")

    cell_offset, decoded = candidates[0]
    region = "freeblock" if any(
        block["offset"] <= cell_offset < block["offset"] + block["size"]
        for block in freeblocks
    ) else "unallocated_page_space"
    return {
        "record": decoded["record"],
        "root_page": root_page,
        "page_size": page_size,
        "cell_offset_in_page": cell_offset,
        "cell_offset_in_file": page_start + cell_offset,
        "payload_size": decoded["payload_size"],
        "sentinel_offset_in_page": sentinel_offset,
        "freeblock_head": freeblock_head,
        "freeblocks": freeblocks,
        "cell_region": region,
        "cell_content_start": cell_content_start,
        "pointer_array_end": pointer_array_end,
        "page_type": page[header_offset],
        "cell_count": cell_count,
    }


def load_manifest_hashes(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    hashes: dict[str, dict[str, Any]] = {}
    with path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            artifact = row["Artifact_Name"]
            role = row.get("Target_Role")
            if role == "WhatsApp_Recovery_Linh":
                hashes.setdefault(artifact, {})["acquisition"] = {
                    "pre_sha256": row["SHA256_Pre_Acquisition"].lower(),
                    "post_sha256": row["SHA256_Post_Acquisition"].lower(),
                    "status": row["Integrity_Status"],
                    "timestamp": row["Timestamp"],
                }
            elif role == "WhatsApp_Recovery_Linh_Revalidation":
                hashes.setdefault(artifact, {})["revalidation"] = {
                    "sha256": row["SHA256_Post_Acquisition"].lower(),
                    "status": row["Integrity_Status"],
                    "timestamp": row["Timestamp"],
                }
    return hashes


def json_default(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.hex()
    raise TypeError(f"Not JSON serializable: {type(value).__name__}")


def run(evidence_dir: Path, output_dir: Path) -> None:
    message_db = evidence_dir / "msgstore.db"
    calls_db = evidence_dir / "wa_calllog_dummy.db"
    message_wal = evidence_dir / "msgstore.db-wal"
    calls_wal = evidence_dir / "wa_calllog_dummy.db-wal"
    required = (message_db, message_wal, calls_db, calls_wal)
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("Required evidence file(s) missing: " + ", ".join(missing))

    tracked_paths = [path for path in evidence_dir.iterdir() if path.is_file()]
    initial_hashes = {path.name: sha256(path) for path in tracked_paths}
    manifest_hashes = load_manifest_hashes(ROOT / "results" / "hash_table.csv")

    message_row_main = fetch_row(message_db, "message", 6, immutable=True)
    call_row_main = fetch_row(calls_db, "call_log", 2, immutable=True)
    if message_row_main is None or call_row_main is None:
        raise RuntimeError("Expected pre-WAL row missing from main database")

    message_root_page = table_root_page(message_db, "message")
    calls_root_page = table_root_page(calls_db, "call_log")
    message_wal_info = wal_summary(message_wal, {message_root_page})
    calls_wal_info = wal_summary(calls_wal, {calls_root_page})

    with tempfile.TemporaryDirectory(prefix="linh_recovery_readonly_") as temporary:
        temp_root = Path(temporary)
        message_copy = temp_root / "msgstore.db"
        calls_copy = temp_root / "wa_calllog_dummy.db"
        for source_db in (message_db, calls_db):
            for suffix in ("", "-wal", "-shm"):
                source = evidence_dir / (source_db.name + suffix)
                if source.is_file():
                    shutil.copy2(source, temp_root / source.name)
        message_row_wal = fetch_row(message_copy, "message", 6, immutable=False)
        call_row_wal = fetch_row(calls_copy, "call_log", 2, immutable=False)

    if message_row_wal is not None or call_row_wal is not None:
        raise RuntimeError("WAL-aware snapshots did not confirm both deletions")

    carved_call = carve_deleted_call(calls_db)
    if carved_call["record"].get("_id") != 4:
        raise RuntimeError("Carved call record did not decode to call_id 4")
    carved_call["record"]["peer_jid"] = None
    jid_connection = open_read_only(calls_db, immutable=True)
    try:
        jid_row_id = carved_call["record"].get("jid_row_id")
        jid = jid_connection.execute(
            "SELECT raw_string FROM jid WHERE _id = ?", (jid_row_id,)
        ).fetchone()
        if jid:
            carved_call["record"]["peer_jid"] = jid[0]
    finally:
        jid_connection.close()

    artifacts = [
        {
            "artifact": "deleted_whatsapp_message",
            "record_id": 6,
            "recovery_method": "immutable_main_database_vs_wal_merged_read_only_snapshot",
            "source_file": message_db.name,
            "source_sha256": initial_hashes[message_db.name],
            "record": message_row_main,
        },
        {
            "artifact": "deleted_whatsapp_call",
            "record_id": 2,
            "recovery_method": "immutable_main_database_vs_wal_merged_read_only_snapshot",
            "source_file": calls_db.name,
            "source_sha256": initial_hashes[calls_db.name],
            "record": call_row_main,
        },
        {
            "artifact": "deleted_whatsapp_missed_call",
            "record_id": 4,
            "recovery_method": "sqlite_table_leaf_record_carving",
            "source_file": calls_db.name,
            "source_sha256": initial_hashes[calls_db.name],
            "evidence_location": {
                "page_number": carved_call["root_page"],
                "cell_offset_in_page": carved_call["cell_offset_in_page"],
                "cell_offset_in_file": carved_call["cell_offset_in_file"],
                "cell_region": carved_call["cell_region"],
            },
            "record": carved_call["record"],
        },
    ]

    hash_rows = []
    for filename, actual in initial_hashes.items():
        if filename in manifest_hashes and "acquisition" in manifest_hashes[filename]:
            acquisition = manifest_hashes[filename]["acquisition"]
            revalidation = manifest_hashes[filename].get("revalidation")
            hash_rows.append(
                {
                    "file": filename,
                    "manifest_pre_sha256": acquisition["pre_sha256"],
                    "manifest_post_sha256": acquisition["post_sha256"],
                    "acquisition_status": acquisition["status"],
                    "current_sha256": actual,
                    "status": "MATCH" if acquisition["post_sha256"] == actual else "MISMATCH",
                    "revalidation_sha256": revalidation["sha256"] if revalidation else None,
                    "revalidation_status": (
                        "MATCH" if revalidation and revalidation["sha256"] == actual else
                        "MISMATCH" if revalidation else None
                    ),
                }
            )
    after_hashes = {path.name: sha256(path) for path in tracked_paths}
    if initial_hashes != after_hashes:
        raise RuntimeError("Source evidence changed during recovery; results were not written")

    output_dir.mkdir(parents=True, exist_ok=True)
    result = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "evidence_directory": str(evidence_dir.resolve()),
        "evidence_hashes": hash_rows,
        "wal": {
            "msgstore.db-wal": message_wal_info,
            "wa_calllog_dummy.db-wal": calls_wal_info,
        },
        "wal_comparison": {
            "message_id_6_in_main_database": message_row_main is not None,
            "message_id_6_in_wal_merged_snapshot": message_row_wal is not None,
            "call_id_2_in_main_database": call_row_main is not None,
            "call_id_2_in_wal_merged_snapshot": call_row_wal is not None,
        },
        "call_id_4_carving": {
            key: value
            for key, value in carved_call.items()
            if key != "record"
        },
        "recovered_records": artifacts,
    }
    json_path = output_dir / "recovered_records.json"
    json_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, default=json_default) + "\n",
        encoding="utf-8",
    )
    print(f"Recovered 3 records to {output_dir.resolve()}")
    print(f"Source evidence unchanged: {initial_hashes == after_hashes}")
    for row in hash_rows:
        if row["status"] != "MATCH":
            print(
                f"WARNING: {row['file']} hash mismatch: "
                f"acquisition_manifest={row['manifest_post_sha256']} "
                f"current={row['current_sha256']}"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", type=Path, default=DEFAULT_EVIDENCE_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    run(args.evidence_dir, args.output_dir)


if __name__ == "__main__":
    main()
