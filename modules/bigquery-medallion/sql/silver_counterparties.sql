CREATE OR REPLACE TABLE `${project_id}.fsi_silver.silver_counterparties` AS
SELECT
  counterparty_id,
  counterparty_name,
  counterparty_type,
  lei,
  country,
  industry,
  internal_rating,
  external_rating_moodys,
  ROUND(ABS(total_exposure), 2) AS total_exposure,
  ROUND(ABS(credit_limit), 2) AS credit_limit,
  status,
  last_review_date,
  ROUND(SAFE_DIVIDE(total_exposure, credit_limit), 4) AS utilization_ratio,
  created_at,
  source_system,
  CURRENT_TIMESTAMP() AS silver_loaded_at
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY counterparty_id ORDER BY created_at DESC) AS rn
  FROM `${project_id}.fsi_bronze.bronze_counterparties`
)
WHERE rn = 1
  AND counterparty_id IS NOT NULL
