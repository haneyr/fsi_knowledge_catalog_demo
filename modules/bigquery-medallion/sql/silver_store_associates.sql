CREATE OR REPLACE TABLE `${project_id}.retail_silver.silver_store_associates` AS
SELECT
  employee_id,
  first_name,
  last_name,
  title,
  department,
  store_id,
  manager_id,
  hire_date,
  employment_status,
  has_finra_license,
  finra_crd_number,
  created_at,
  source_system,
  CURRENT_TIMESTAMP() AS silver_loaded_at
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY employee_id ORDER BY created_at DESC) AS rn
  FROM `${project_id}.retail_bronze.bronze_store_associates`
)
WHERE rn = 1
  AND employee_id IS NOT NULL
