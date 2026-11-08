#!/usr/bin/env bash
# Extract WhatsApp and Telegram artifacts from a rooted Android 11 AVD
# Usage (Git Bash): bash scripts/cuong_extraction/extract_wa_tg.sh ./dumps

set -euo pipefail

OUT_DIR="${1:-./dumps}"
HASH_CSV="./results/hash_table.csv"
TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

mkdir -p "$OUT_DIR/whatsapp" "$OUT_DIR/telegram" "./results"

if [ ! -f "$HASH_CSV" ]; then
    echo "timestamp_utc,member,app_or_source,device_path,local_file,size_bytes,sha256_on_device,sha256_after_pull,match_status" > "$HASH_CSV"
fi

echo "[*] Switching adb to root..."
adb root >/dev/null
adb wait-for-device

pull_and_verify() {
    local app="$1"
    local remote_path="$2"
    local local_dir="$3"
    local base_name
    base_name="$(basename "$remote_path")"
    local local_path="$local_dir/$base_name"

    if adb shell "[ -f '$remote_path' ]"; then
        local remote_hash
        remote_hash="$(adb shell "sha256sum '$remote_path'" | awk '{print $1}' | tr -d '\r')"
        adb pull "$remote_path" "$local_path" >/dev/null
        local local_hash
        local_hash="$(sha256sum "$local_path" | awk '{print $1}')"
        local size_bytes
        size_bytes="$(wc -c < "$local_path" | tr -d ' ')"
        local status="MATCH"
        if [ "$remote_hash" != "$local_hash" ]; then
            status="MISMATCH"
        fi
        echo "$TIMESTAMP,Cuong,$app,$remote_path,$local_path,$size_bytes,$remote_hash,$local_hash,$status" >> "$HASH_CSV"
        echo "  [+] $base_name ($status): $local_hash"
    else
        echo "  [-] Not found on device (skipped): $remote_path"
    fi
}

echo "[*] Pulling WhatsApp databases (including WAL/SHM)..."
for ext in "" "-wal" "-shm"; do
    pull_and_verify "WhatsApp" "/data/data/com.whatsapp/databases/msgstore.db${ext}" "$OUT_DIR/whatsapp"
    pull_and_verify "WhatsApp" "/data/data/com.whatsapp/databases/wa.db${ext}" "$OUT_DIR/whatsapp"
done
pull_and_verify "WhatsApp" "/data/data/com.whatsapp/files/key" "$OUT_DIR/whatsapp"

echo "[*] Pulling Telegram databases (including WAL/SHM) and userconfing.xml..."
TG_PKG="org.telegram.messenger"
if adb shell "[ -d '/data/data/org.telegram.messenger.web' ]"; then
    TG_PKG="org.telegram.messenger.web"
fi
for ext in "" "-wal" "-shm"; do
    pull_and_verify "Telegram" "/data/data/${TG_PKG}/files/cache4.db${ext}" "$OUT_DIR/telegram"
done
pull_and_verify "Telegram" "/data/data/${TG_PKG}/shared_prefs/userconfing.xml" "$OUT_DIR/telegram"

echo "[*] Done. Hashes appended to $HASH_CSV"
