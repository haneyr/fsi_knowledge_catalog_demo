CREATE OR REPLACE TABLE `${project_id}.retail_silver.silver_category_benchmarks` AS
SELECT
  benchmark_id,
  benchmark_name,
  as_of_date,
  daily_return,
  mtd_return,
  ytd_return,
  ROUND(ABS(index_level), 2) AS index_level,
  annualized_volatility,
  created_at,
  source_system,
  CURRENT_TIMESTAMP() AS silver_loaded_at
FROM `${project_id}.retail_bronze.bronze_category_benchmarks`
WHERE benchmark_id IS NOT NULL
