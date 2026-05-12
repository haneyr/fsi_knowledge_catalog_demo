CREATE OR REPLACE TABLE `${project_id}.fsi_silver.silver_branches` AS
SELECT
  branch_id,
  branch_name,
  address,
  city,
  state,
  branch_type,
  region,
  district_manager_id,
  employee_count,
  longitude,
  latitude,
  open_date,
  status,
  created_at,
  source_system,
  CURRENT_TIMESTAMP() AS silver_loaded_at
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY branch_id ORDER BY created_at DESC) AS rn
  FROM `${project_id}.fsi_bronze.bronze_branches`
)
WHERE rn = 1
  AND branch_id IS NOT NULL
