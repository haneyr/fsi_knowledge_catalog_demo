CREATE OR REPLACE VIEW `${project_id}.retail_dashboards.vw_compliance_summary` AS
SELECT
  metric_category,
  metric_name,
  metric_value,
  threshold,
  status,
  as_of_date
FROM `${project_id}.retail_gold.gold_compliance_dashboard`
