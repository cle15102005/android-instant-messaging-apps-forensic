#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQLite Header & Journal Mode Inspector (Task 2 - Linh)
Reads raw header bytes of a SQLite database without opening a SQLite connection
(guaranteeing zero WAL checkpoint side effects):
  - Offset 18 & 19: file format write/read version (1 = Legacy rollback, 2 = WAL)
  - Offset 52..55: incremental/auto_vacuum setting (0 = NONE, 1 = FULL, 2 = INCREMENTAL)
"""
import argparse
import hashlib
from pathlib import Path


def inspect_header(db_path: Path) -> dict:
    raw = db_path.read_bytes()
    sha256 = hashlib.sha256(raw).hexdigest()
    magic = raw[:16]
    is_sqlite = magic == b"SQLite format 3\x00"
    write_ver = raw[18] if len(raw) > 19 else -1
    read_ver = raw[19] if len(raw) > 19 else -1
    auto_vacuum = int.from_bytes(raw[52:56], "big") if len(raw) >= 56 else -1
    return {
        "file": str(db_path),
        "is_plaintext_sqlite": is_sqlite,
        "write_version_offset18": write_ver,
        "read_version_offset19": read_ver,
        "wal_mode": (write_ver == 2 and read_ver == 2),
        "auto_vacuum_offset52": auto_vacuum,
        "sha256": sha256,
    }


def main():
    parser = argparse.ArgumentParser(description="Safe read-only SQLite header inspector")
    parser.add_argument("db", nargs="?", help="Path to SQLite .db file")
    args = parser.parse_args()
    if not args.db:
        parser.print_help()
        return
    info = inspect_header(Path(args.db))
    for k, v in info.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
