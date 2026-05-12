CREATE OR REPLACE TABLE `${project_id}.fsi_silver.silver_employees` AS
SELECT
  employee_id,
  first_name,
  last_name,
  title,
  department,
  branch_id,
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
  FROM `${project_id}.fsi_bronze.bronze_employees`
)
WHERE rn = 1
  AND employee_id IS NOT NULL
