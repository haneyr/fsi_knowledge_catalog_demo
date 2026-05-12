CREATE OR REPLACE TABLE `${project_id}.fsi_silver.silver_cost_centers` AS
SELECT
  cost_center_id,
  cost_center_name,
  center_type,
  division,
  manager_id,
  ROUND(ABS(annual_budget), 0) AS annual_budget,
  status,
  created_at,
  source_system,
  CURRENT_TIMESTAMP() AS silver_loaded_at
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY cost_center_id ORDER BY created_at DESC) AS rn
  FROM `${project_id}.fsi_bronze.bronze_cost_centers`
)
WHERE rn = 1
  AND cost_center_id IS NOT NULL
