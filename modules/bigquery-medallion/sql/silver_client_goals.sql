CREATE OR REPLACE TABLE `${project_id}.fsi_silver.silver_client_goals` AS
SELECT
  goal_id,
  wm_client_id,
  goal_type,
  goal_name,
  ROUND(ABS(target_amount), 0) AS target_amount,
  ROUND(ABS(current_amount), 0) AS current_amount,
  ROUND(SAFE_DIVIDE(current_amount, target_amount), 4) AS progress_pct,
  target_date,
  status,
  priority_rank,
  created_at,
  source_system,
  CURRENT_TIMESTAMP() AS silver_loaded_at
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY goal_id ORDER BY created_at DESC) AS rn
  FROM `${project_id}.fsi_bronze.bronze_client_goals`
)
WHERE rn = 1
  AND goal_id IS NOT NULL
  AND wm_client_id IS NOT NULL
