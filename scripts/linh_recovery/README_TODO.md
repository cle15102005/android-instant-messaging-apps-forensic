# Role 3 (Nguyen Ngoc Linh - 20235599): Deleted Message, Call Log & SMS Recovery (WAL & B-Tree Carving)

## Raw Evidence Inputs (Provided by Cuong in `dumps/for_linh/`)
1. `msgstore.db` + `msgstore.db-wal` + `msgstore.db-shm` (Contains `msg_id = 6` deleted via *Delete for me* in `.db-wal` prior to WAL checkpointing).
2. `wa_calllog_dummy.db` + `wa_calllog_dummy.db-wal` + `wa_calllog_dummy.db-shm` (Contains `call_id = 2` deleted in `.db-wal` pre-checkpoint, and `call_id = 4` deleted post-checkpoint in a B-Tree leaf page freeblock).
3. `mmssms.db` (Android Telephony SMS database in Rollback Journal mode `0x01`, containing deleted SMS records `_id = 3` and `_id = 5` in B-Tree freeblocks).
4. `calllog.db` (Android Contacts Provider Call Log database in Rollback Journal mode `0x01`, containing deleted Call Log records `_id = 2` and `_id = 4` in B-Tree freeblocks).

## Tasks for Linh (TODO)
1. Run `sqlite_header_check.py` on all target databases to verify page size (`4096` bytes) and journal mode (`0x02` WAL vs. `0x01` Rollback Journal).
2. Implement pre-checkpoint WAL comparison (`?immutable=1` vs. WAL-merged state) to recover `msg_id = 6` from `msgstore.db` and `call_id = 2` from `wa_calllog_dummy.db`.
3. Use `FQLite` or a custom Python B-Tree freeblock carver to recover post-checkpoint deleted records (`call_id = 4` in `wa_calllog_dummy.db`, SMS `_id = 3, 5` in `mmssms.db`, and calls `_id = 2, 4` in `calllog.db`).
4. Export recovered records to `results/carved_sms_calls/` and complete Section 4.3 of the LaTeX report.
