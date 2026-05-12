CREATE OR REPLACE TABLE `${project_id}.fsi_silver.silver_audit_events` AS
SELECT
  audit_event_id,
  event_timestamp,
  user_id,
  event_type,
  system_name,
  resource_accessed,
  result,
  source_ip,
  sox_relevant,
  created_at,
  source_system,
  CURRENT_TIMESTAMP() AS silver_loaded_at
FROM `${project_id}.fsi_bronze.bronze_audit_events`
WHERE audit_event_id IS NOT NULL
