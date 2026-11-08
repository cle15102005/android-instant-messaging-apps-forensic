# Standardized CSV Schemas

All scripts in `scripts/` must output CSV files conforming to these exact column headers so they can be merged seamlessly in Week 3 (Integration Checkpoint).

## 1. `results/hash_table.csv` (Cuong, Linh, Huy)
```csv
timestamp_utc,member,app_or_source,device_path,local_file,size_bytes,sha256_on_device,sha256_after_pull,match_status
```

## 2. `results/allowbackup_result.csv` (Cuong)
```csv
app,package_name,version_name,target_sdk,allow_backup_flag,notes
```

## 3. `results/recovery_report.csv` (Linh)
```csv
db_name,test_case,wal_mode_offset18,auto_vacuum_offset52,secure_delete_verified,deleted_count,recovered_wal,recovered_freelist,partial_count,recovery_rate_percent,notes
```

## 4. `results/artifact_inventory.csv` (Hai)
```csv
app,artifact_category,device_path,file_type,size_bytes,mtime_utc,forensic_value,extracted_summary,sha256
```
