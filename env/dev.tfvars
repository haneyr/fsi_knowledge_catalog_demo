# Dev environment — rapid testing. Deployed continuously on push to main.
locals {
  project_id         = "fsi-kc-demo-dev"
  region             = "us-central1"
  multi_region       = "us"
  snowflake_database = "NEXUS_MARKET_DATA_DEV"
}
