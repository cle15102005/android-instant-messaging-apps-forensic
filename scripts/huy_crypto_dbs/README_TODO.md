# Role 2 (Hoang Quoc Huy - 20235594): WhatsApp E2EE Cryptographic & Auxiliary SQLite Databases

## Raw Evidence Inputs (Provided by Cuong in `dumps/for_huy/`)
1. `axolotl.db` + `axolotl.db-wal` + `axolotl.db-shm` (Signal Protocol E2EE database: `identities`, `prekeys` [1,624 keys], `signed_prekeys`, `prekey_uploads`, `sessions`, `sender_keys`).
2. `key` (`158 bytes` local `.crypt14`/`.crypt15` backup decryption key extracted from `/data/data/com.whatsapp/files/key`).
3. Auxiliary WhatsApp SQLite databases (`chatsettings.db`, `companion_devices.db`, `status.db`, `stickers.db`, `media.db`, `sync.db` + `.db-wal` files).

## Tasks for Huy (TODO)
1. Write a Python inspection script in `scripts/huy_crypto_dbs/` to query `axolotl.db` (merging `.db-wal` in a temporary directory so original hashes in `results/hash_table.csv` remain unchanged) and summarize the Signal Protocol key tables.
2. Parse the 158-byte `files/key` binary structure (27-byte header, server salt, and 32-byte AES-256 key at offset `126..158`).
3. Inventory the tables and active rows across the auxiliary WhatsApp databases (`status.db`, `stickers.db`, `chatsettings.db`, `companion_devices.db`, `media.db`, `sync.db`).
4. Export results to `results/reconstruction_logs/huy_crypto_dbs/` and complete Section 4.2 of the LaTeX report.
