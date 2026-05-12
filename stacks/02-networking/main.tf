variable "project_id" { type = string }
variable "region" {
  type    = string
  default = "us-central1"
}

module "networking" {
  source     = "../../modules/networking"
  project_id = var.project_id
  region     = var.region
}
