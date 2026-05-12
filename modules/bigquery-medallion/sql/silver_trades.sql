CREATE OR REPLACE TABLE `${project_id}.fsi_silver.silver_trades` AS
SELECT
  trade_id,
  portfolio_id,
  security_id,
  trade_type,
  ROUND(ABS(quantity), 4) AS quantity,
  ROUND(ABS(price), 2) AS price,
  ROUND(ABS(gross_amount), 2) AS gross_amount,
  ROUND(ABS(commission), 2) AS commission,
  ROUND(ABS(fees), 2) AS fees,
  ROUND(ABS(gross_amount) - ABS(commission) - ABS(fees), 2) AS net_amount,
  trade_date,
  settlement_date,
  status,
  order_type,
  advisor_id,
  solicitation_type,
  created_at,
  source_system,
  CURRENT_TIMESTAMP() AS silver_loaded_at
FROM `${project_id}.fsi_bronze.bronze_trades`
WHERE trade_id IS NOT NULL
  AND portfolio_id IS NOT NULL
