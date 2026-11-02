#!/usr/bin/env bash
# Inspect AndroidManifest.xml of WhatsApp, Telegram, and Zalo APKs for allowBackup and targetSdkVersion
# Usage: bash scripts/cuong_extraction/check_allowbackup.sh ./apks

set -euo pipefail

APK_DIR="${1:-./apks}"
OUT_CSV="./results/allowbackup_result.csv"
mkdir -p ./results

echo "app,package_name,version_name,target_sdk,allow_backup_flag,notes" > "$OUT_CSV"

for apk in "$APK_DIR"/*.apk; do
    [ -e "$apk" ] || continue
    echo "[*] Analyzing $apk..."
    badging="$(aapt dump badging "$apk" 2>/dev/null || true)"
    pkg="$(echo "$badging" | awk -F"'" '/package: name=/{print $2}')"
    ver="$(echo "$badging" | awk -F"'" '/versionName=/{print $6}')"
    sdk="$(echo "$badging" | awk -F"'" '/targetSdkVersion:/{print $2}')"
    xml="$(aapt dump xmltree "$apk" AndroidManifest.xml 2>/dev/null || true)"
    if echo "$xml" | grep -qi "allowBackup.*0x0$"; then
        allow="false"
    elif echo "$xml" | grep -qi "allowBackup.*0xffffffff$"; then
        allow="true"
    else
        allow="not_declared_default_true"
    fi
    echo "$(basename "$apk"),$pkg,$ver,$sdk,$allow,Checked via aapt" >> "$OUT_CSV"
done

echo "[*] Results saved to $OUT_CSV"
