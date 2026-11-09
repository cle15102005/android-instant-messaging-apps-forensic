# Role 3 (Nguyen Ngoc Linh - 20235599): Deleted WhatsApp Message & Call Log Recovery

## Evidence Inputs (`for_linh/`)
1. `msgstore.db` + `msgstore.db-wal` + `msgstore.db-shm` (Contains WhatsApp text message `msg_id = 6` deleted via *Delete for me* in `.db-wal` prior to WAL checkpointing).
2. `wa_calllog_dummy.db` + `wa_calllog_dummy.db-wal` + `wa_calllog_dummy.db-shm` (Contains WhatsApp voice call `call_id = 2` deleted in `.db-wal`, and a deleted WhatsApp missed call `call_id = 4` with a surviving B-tree page record).

## Completed Recovery
1. `sqlite_header_check.py` confirmed plaintext SQLite and WAL versions (`write_version=2`, `read_version=2`). Both database and WAL page sizes are 4096 bytes.
2. `recover_deleted_records.py` compared immutable main-database reads against WAL-aware, read-only reads of temporary copies. It recovered `message._id=6` and `call_log._id=2` from the main-database snapshots; both records are absent in the corresponding WAL-merged snapshots.
3. The script carved `call_log._id=4` (`WA_CALL_DEL_FREEBLOCK_04`) from the `call_log` table-leaf page. The cell is at page 4, offset 3811 (file offset 16099), and decodes to a 72-byte payload.
4. The page header has no linked freeblock (`freeblock head = 0`). The surviving cell is in unallocated page space, so this is B-tree page carving, not carving a linked freeblock.
5. Outputs: `results/carved_sms_calls/recovered_records.json` and `results/carved_sms_calls/RECOVERY_PROCESS.md`. The latter contains the detailed steps and recovered values.

## Integrity Caveat
The acquisition entry in `results/hash_table.csv` records `ad8a38eff610717d43ec910beaee98749efd9d71071dec286b76992b5832860a` for `wa_calllog_dummy.db-wal`. The current SHA-256 `eec6e9816f7d8f00a94a995fbbcece280f3701cffa31fa1e457eb24cde11e287` is recorded in a separate `WhatsApp_Recovery_Linh_Revalidation` row; the original acquisition entry is preserved. The database and other relevant evidence hashes match. The difference between acquisition and current WAL remains unexplained; the recovery uses the current file and does not modify the evidence.
