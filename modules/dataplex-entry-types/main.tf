# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

variable "project_id" { type = string }
variable "region" { type = string }

# ============================================================
# Source System Entry Types
# ============================================================

# --- ATLAS (IBM DB2 Mainframe) ---
resource "google_dataplex_entry_type" "db2_instance" {
  project       = var.project_id
  location      = var.region
  entry_type_id = "db2-instance"
  display_name  = "DB2 Mainframe Instance"
  description   = "Represents an IBM DB2 for z/OS instance"
  type_aliases  = ["DATABASE"]
  platform      = "IBM"
  system        = "DB2 for z/OS"
}

resource "google_dataplex_entry_type" "db2_schema" {
  project       = var.project_id
  location      = var.region
  entry_type_id = "db2-schema"
  display_name  = "DB2 Schema"
  description   = "Represents a schema within a DB2 instance"
  type_aliases  = ["DATABASE_SCHEMA"]
  platform      = "IBM"
  system        = "DB2 for z/OS"
}

resource "google_dataplex_entry_type" "db2_table" {
  project       = var.project_id
  location      = var.region
  entry_type_id = "db2-table"
  display_name  = "DB2 Table"
  description   = "Represents a table within a DB2 schema"
  type_aliases  = ["TABLE"]
  platform      = "IBM"
  system        = "DB2 for z/OS"
}

# --- FORTUNA (Temenos T24) ---
resource "google_dataplex_entry_type" "temenos_instance" {
  project       = var.project_id
  location      = var.region
  entry_type_id = "temenos-instance"
  display_name  = "Temenos T24 Instance"
  description   = "Represents a Temenos T24 core banking instance"
  type_aliases  = ["DATABASE"]
  platform      = "Temenos"
  system        = "T24 Transact"
}

resource "google_dataplex_entry_type" "temenos_schema" {
  project       = var.project_id
  location      = var.region
  entry_type_id = "temenos-schema"
  display_name  = "Temenos Schema"
  description   = "Represents a module/schema within Temenos T24"
  type_aliases  = ["DATABASE_SCHEMA"]
  platform      = "Temenos"
  system        = "T24 Transact"
}

resource "google_dataplex_entry_type" "temenos_table" {
  project       = var.project_id
  location      = var.region
  entry_type_id = "temenos-table"
  display_name  = "Temenos Table"
  description   = "Represents a table within Temenos T24"
  type_aliases  = ["TABLE"]
  platform      = "Temenos"
  system        = "T24 Transact"
}

# --- ARGUS (SAP S/4HANA) ---
resource "google_dataplex_entry_type" "sap_instance" {
  project       = var.project_id
  location      = var.region
  entry_type_id = "sap-instance"
  display_name  = "SAP S/4HANA Instance"
  description   = "Represents an SAP S/4HANA system"
  type_aliases  = ["DATABASE"]
  platform      = "SAP"
  system        = "S/4HANA"
}

resource "google_dataplex_entry_type" "sap_schema" {
  project       = var.project_id
  location      = var.region
  entry_type_id = "sap-schema"
  display_name  = "SAP Schema"
  description   = "Represents a schema within SAP HANA"
  type_aliases  = ["DATABASE_SCHEMA"]
  platform      = "SAP"
  system        = "S/4HANA"
}

resource "google_dataplex_entry_type" "sap_table" {
  project       = var.project_id
  location      = var.region
  entry_type_id = "sap-table"
  display_name  = "SAP Table"
  description   = "Represents a table within SAP HANA"
  type_aliases  = ["TABLE"]
  platform      = "SAP"
  system        = "S/4HANA"
}

# ============================================================
# Source System Aspect Types (marker aspects)
# ============================================================
resource "google_dataplex_aspect_type" "db2_instance" {
  project        = var.project_id
  location       = var.region
  aspect_type_id = "db2-instance"
  display_name   = "DB2 Instance"
  description    = "Marker aspect for DB2 Instance entries"
  metadata_template = jsonencode({
    name         = "db2_instance"
    type         = "record"
    recordFields = []
  })
}

resource "google_dataplex_aspect_type" "db2_schema" {
  project        = var.project_id
  location       = var.region
  aspect_type_id = "db2-schema"
  display_name   = "DB2 Schema"
  description    = "Marker aspect for DB2 Schema entries"
  metadata_template = jsonencode({
    name         = "db2_schema"
    type         = "record"
    recordFields = []
  })
}

resource "google_dataplex_aspect_type" "db2_table" {
  project        = var.project_id
  location       = var.region
  aspect_type_id = "db2-table"
  display_name   = "DB2 Table"
  description    = "Marker aspect for DB2 Table entries"
  metadata_template = jsonencode({
    name         = "db2_table"
    type         = "record"
    recordFields = []
  })
}

resource "google_dataplex_aspect_type" "temenos_instance" {
  project        = var.project_id
  location       = var.region
  aspect_type_id = "temenos-instance"
  display_name   = "Temenos Instance"
  description    = "Marker aspect for Temenos Instance entries"
  metadata_template = jsonencode({
    name         = "temenos_instance"
    type         = "record"
    recordFields = []
  })
}

resource "google_dataplex_aspect_type" "temenos_table" {
  project        = var.project_id
  location       = var.region
  aspect_type_id = "temenos-table"
  display_name   = "Temenos Table"
  description    = "Marker aspect for Temenos Table entries"
  metadata_template = jsonencode({
    name         = "temenos_table"
    type         = "record"
    recordFields = []
  })
}

resource "google_dataplex_aspect_type" "sap_instance" {
  project        = var.project_id
  location       = var.region
  aspect_type_id = "sap-instance"
  display_name   = "SAP Instance"
  description    = "Marker aspect for SAP Instance entries"
  metadata_template = jsonencode({
    name         = "sap_instance"
    type         = "record"
    recordFields = []
  })
}

resource "google_dataplex_aspect_type" "sap_table" {
  project        = var.project_id
  location       = var.region
  aspect_type_id = "sap-table"
  display_name   = "SAP Table"
  description    = "Marker aspect for SAP Table entries"
  metadata_template = jsonencode({
    name         = "sap_table"
    type         = "record"
    recordFields = []
  })
}

# ============================================================
# FSI Custom Aspect Types (global for cross-region use)
# ============================================================

resource "google_dataplex_aspect_type" "data_classification" {
  project        = var.project_id
  location       = "global"
  aspect_type_id = "fsi-data-classification"
  display_name   = "Data Classification"
  description    = "Data sensitivity and PII classification for financial services data"
  metadata_template = jsonencode({
    name = "data_classification"
    type = "record"
    recordFields = [
      { name = "classification_level", type = "enum", index = 1, constraints = { required = true }, annotations = { displayName = "Classification Level" },
        enumValues = [{ name = "Public", index = 1 }, { name = "Internal", index = 2 }, { name = "Confidential", index = 3 }, { name = "Restricted", index = 4 }, { name = "Highly Restricted", index = 5 }] },
      { name = "pii_category", type = "enum", index = 2, annotations = { displayName = "PII Category" },
        enumValues = [{ name = "Direct Identifier", index = 1 }, { name = "Quasi Identifier", index = 2 }, { name = "Financial Data", index = 3 }, { name = "Account Data", index = 4 }, { name = "Not PII", index = 5 }] },
      { name = "requires_encryption", type = "bool", index = 3, annotations = { displayName = "Requires Encryption" } },
      { name = "requires_masking", type = "bool", index = 4, annotations = { displayName = "Requires Masking" } },
      { name = "regulatory_scope", type = "string", index = 5, annotations = { displayName = "Regulatory Scope" } },
    ]
  })
}

resource "google_dataplex_aspect_type" "data_retention" {
  project        = var.project_id
  location       = "global"
  aspect_type_id = "fsi-data-retention"
  display_name   = "Data Retention Policy"
  description    = "Regulatory data retention requirements for financial services data"
  metadata_template = jsonencode({
    name = "data_retention"
    type = "record"
    recordFields = [
      { name = "retention_period_years", type = "int", index = 1, constraints = { required = true }, annotations = { displayName = "Retention Period (Years)" } },
      { name = "governing_regulation", type = "string", index = 2, annotations = { displayName = "Governing Regulation" } },
      { name = "retention_start_event", type = "string", index = 3, annotations = { displayName = "Retention Start Event" } },
      { name = "archival_required", type = "bool", index = 4, annotations = { displayName = "Archival Required" } },
      { name = "destruction_method", type = "enum", index = 5, annotations = { displayName = "Destruction Method" },
        enumValues = [{ name = "Secure Purge", index = 1 }, { name = "Crypto Shredding", index = 2 }, { name = "Physical Destruction", index = 3 }, { name = "Not Applicable", index = 4 }] },
    ]
  })
}

resource "google_dataplex_aspect_type" "regulatory_compliance" {
  project        = var.project_id
  location       = "global"
  aspect_type_id = "fsi-regulatory-compliance"
  display_name   = "Regulatory Compliance"
  description    = "Regulatory compliance status and applicable regulations"
  metadata_template = jsonencode({
    name = "regulatory_compliance"
    type = "record"
    recordFields = [
      { name = "applicable_regulations", type = "string", index = 1, constraints = { required = true }, annotations = { displayName = "Applicable Regulations" } },
      { name = "compliance_status", type = "enum", index = 2, constraints = { required = true }, annotations = { displayName = "Compliance Status" },
        enumValues = [{ name = "Compliant", index = 1 }, { name = "Partially Compliant", index = 2 }, { name = "Non-Compliant", index = 3 }, { name = "Under Review", index = 4 }] },
      { name = "last_audit_date", type = "string", index = 3, annotations = { displayName = "Last Audit Date" } },
      { name = "audit_frequency", type = "enum", index = 4, annotations = { displayName = "Audit Frequency" },
        enumValues = [{ name = "Annual", index = 1 }, { name = "Semi-Annual", index = 2 }, { name = "Quarterly", index = 3 }, { name = "Continuous", index = 4 }] },
      { name = "compliance_notes", type = "string", index = 5, annotations = { displayName = "Compliance Notes" } },
    ]
  })
}

resource "google_dataplex_aspect_type" "data_lineage_metadata" {
  project        = var.project_id
  location       = "global"
  aspect_type_id = "fsi-data-lineage-metadata"
  display_name   = "Data Lineage Metadata"
  description    = "Source system and data flow information"
  metadata_template = jsonencode({
    name = "data_lineage"
    type = "record"
    recordFields = [
      { name = "source_system", type = "string", index = 1, constraints = { required = true }, annotations = { displayName = "Source System" } },
      { name = "ingestion_method", type = "enum", index = 2, annotations = { displayName = "Ingestion Method" },
        enumValues = [{ name = "IBM CDC Replication", index = 1 }, { name = "Temenos Extract API", index = 2 }, { name = "SAP SLT Replication", index = 3 }, { name = "Batch File Extract", index = 4 }, { name = "Database Replication", index = 5 }, { name = "API Integration", index = 6 }, { name = "SWIFT/FIX Message", index = 7 }] },
      { name = "refresh_frequency", type = "enum", index = 3, annotations = { displayName = "Refresh Frequency" },
        enumValues = [{ name = "Real-time", index = 1 }, { name = "Intraday", index = 2 }, { name = "End-of-Day", index = 3 }, { name = "Daily", index = 4 }, { name = "Weekly", index = 5 }, { name = "Monthly", index = 6 }] },
      { name = "data_flow_path", type = "string", index = 4, annotations = { displayName = "Data Flow Path" } },
    ]
  })
}

resource "google_dataplex_aspect_type" "access_control" {
  project        = var.project_id
  location       = "global"
  aspect_type_id = "fsi-access-control"
  display_name   = "Access Control Policy"
  description    = "Role-based access control and authorization requirements"
  metadata_template = jsonencode({
    name = "access_control"
    type = "record"
    recordFields = [
      { name = "access_level", type = "enum", index = 1, constraints = { required = true }, annotations = { displayName = "Access Level" },
        enumValues = [{ name = "Public", index = 1 }, { name = "Internal", index = 2 }, { name = "Restricted", index = 3 }, { name = "Confidential", index = 4 }, { name = "Highly Restricted", index = 5 }] },
      { name = "authorized_roles", type = "string", index = 2, constraints = { required = true }, annotations = { displayName = "Authorized Roles" } },
      { name = "requires_mfa", type = "bool", index = 3, annotations = { displayName = "Requires MFA" } },
      { name = "need_to_know_applies", type = "bool", index = 4, annotations = { displayName = "Need-to-Know Applies" } },
      { name = "audit_all_access", type = "bool", index = 5, annotations = { displayName = "Audit All Access" } },
    ]
  })
}

resource "google_dataplex_aspect_type" "risk_classification" {
  project        = var.project_id
  location       = "global"
  aspect_type_id = "fsi-risk-classification"
  display_name   = "Risk Data Classification"
  description    = "Risk management classification and model dependency tagging"
  metadata_template = jsonencode({
    name = "risk_classification"
    type = "record"
    recordFields = [
      { name = "risk_category", type = "enum", index = 1, constraints = { required = true }, annotations = { displayName = "Risk Category" },
        enumValues = [{ name = "Credit Risk", index = 1 }, { name = "Market Risk", index = 2 }, { name = "Operational Risk", index = 3 }, { name = "Liquidity Risk", index = 4 }, { name = "Compliance Risk", index = 5 }, { name = "Not Risk Data", index = 6 }] },
      { name = "model_dependency", type = "enum", index = 2, annotations = { displayName = "Model Dependency" },
        enumValues = [{ name = "Model Input", index = 1 }, { name = "Model Output", index = 2 }, { name = "Model Calibration", index = 3 }, { name = "Not Model Related", index = 4 }] },
      { name = "materiality_level", type = "enum", index = 3, annotations = { displayName = "Materiality Level" },
        enumValues = [{ name = "Material", index = 1 }, { name = "Significant", index = 2 }, { name = "Moderate", index = 3 }, { name = "Immaterial", index = 4 }] },
      { name = "sox_relevant", type = "bool", index = 4, annotations = { displayName = "SOX Relevant" } },
    ]
  })
}

resource "google_dataplex_aspect_type" "regulatory_reporting" {
  project        = var.project_id
  location       = "global"
  aspect_type_id = "fsi-regulatory-reporting"
  display_name   = "Regulatory Reporting Mapping"
  description    = "Maps data elements to regulatory report line items"
  metadata_template = jsonencode({
    name = "regulatory_reporting"
    type = "record"
    recordFields = [
      { name = "report_name", type = "string", index = 1, annotations = { displayName = "Report Name" } },
      { name = "filing_frequency", type = "enum", index = 2, annotations = { displayName = "Filing Frequency" },
        enumValues = [{ name = "Daily", index = 1 }, { name = "Monthly", index = 2 }, { name = "Quarterly", index = 3 }, { name = "Semi-Annual", index = 4 }, { name = "Annual", index = 5 }, { name = "Ad Hoc", index = 6 }] },
      { name = "regulatory_body", type = "enum", index = 3, annotations = { displayName = "Regulatory Body" },
        enumValues = [{ name = "OCC", index = 1 }, { name = "Federal Reserve", index = 2 }, { name = "FDIC", index = 3 }, { name = "SEC", index = 4 }, { name = "FINRA", index = 5 }, { name = "FinCEN", index = 6 }, { name = "CFPB", index = 7 }, { name = "State Regulator", index = 8 }] },
      { name = "schedule_line_item", type = "string", index = 4, annotations = { displayName = "Schedule / Line Item" } },
    ]
  })
}

# ============================================================
# Entry Groups
# ============================================================
resource "google_dataplex_entry_group" "atlas_db2" {
  project        = var.project_id
  location       = var.region
  entry_group_id = "atlas-core-banking"
  display_name   = "ATLAS Core Banking (DB2)"
  description    = "IBM DB2 mainframe entries for the ATLAS core banking system"
}

resource "google_dataplex_entry_group" "fortuna_wealth" {
  project        = var.project_id
  location       = var.region
  entry_group_id = "fortuna-wealth-mgmt"
  display_name   = "FORTUNA Wealth Management (Temenos)"
  description    = "Temenos T24 entries for the FORTUNA wealth management platform"
}

resource "google_dataplex_entry_group" "argus_risk" {
  project        = var.project_id
  location       = var.region
  entry_group_id = "argus-finance-risk"
  display_name   = "ARGUS Finance & Risk (SAP)"
  description    = "SAP S/4HANA entries for the ARGUS finance and risk management system"
}
