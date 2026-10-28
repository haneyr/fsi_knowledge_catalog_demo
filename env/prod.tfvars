# Prod environment — stable demo. Deployed on release tag (v*.*.*).
locals {
  project_id         = "retail-kc-demo-prod"
  region             = "us-central1"
  multi_region       = "us"
  snowflake_database = "NEXUS_MARKET_DATA"
}
