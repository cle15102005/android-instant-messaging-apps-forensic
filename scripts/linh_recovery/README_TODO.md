# Role 3 (Nguyen Ngoc Linh - 20235599): Deleted WhatsApp Message & Call Log Recovery (WAL & B-Tree Carving)

## Raw Evidence Inputs (Provided by Cuong in `dumps/for_linh/`)
1. `msgstore.db` + `msgstore.db-wal` + `msgstore.db-shm` (Contains WhatsApp text message `msg_id = 6` deleted via *Delete for me* in `.db-wal` prior to WAL checkpointing).
2. `wa_calllog_dummy.db` + `wa_calllog_dummy.db-wal` + `wa_calllog_dummy.db-shm` (Contains WhatsApp voice call `call_id = 2` deleted in `.db-wal` pre-checkpoint, and WhatsApp missed call `call_id = 4` deleted post-checkpoint in a B-Tree leaf page freeblock of the `call_log` table).

## Tasks for Linh (TODO)
1. Run `sqlite_header_check.py` on `msgstore.db` and `wa_calllog_dummy.db` to verify page size (`4096` bytes) and journal mode (`0x02` WAL).
2. Implement pre-checkpoint WAL comparison (`?immutable=1` vs. WAL-merged state) to recover deleted WhatsApp text message `msg_id = 6` from `msgstore.db` and deleted WhatsApp voice call `call_id = 2` from `wa_calllog_dummy.db`.
3. Use `FQLite` or a custom Python B-Tree freeblock carver to recover post-checkpoint deleted WhatsApp call log `call_id = 4` (`WA_CALL_DEL_FREEBLOCK_04`) from `wa_calllog_dummy.db`.
4. Export recovered records to `results/carved_sms_calls/` and complete Section 4.3 of the LaTeX report.
