CREATE OR REPLACE VIEW `${project_id}.fsi_dashboards.vw_regulatory_summary` AS
SELECT
  metric_category,
  metric_name,
  metric_value,
  threshold,
  status,
  as_of_date
FROM `${project_id}.fsi_gold.gold_regulatory_dashboard`
