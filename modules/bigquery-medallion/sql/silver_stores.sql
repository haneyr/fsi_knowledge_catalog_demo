CREATE OR REPLACE TABLE `${project_id}.retail_silver.silver_stores` AS
SELECT
  store_id,
  store_name,
  address,
  city,
  state,
  store_format,
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
  SELECT *, ROW_NUMBER() OVER (PARTITION BY store_id ORDER BY created_at DESC) AS rn
  FROM `${project_id}.retail_bronze.bronze_stores`
)
WHERE rn = 1
  AND store_id IS NOT NULL
