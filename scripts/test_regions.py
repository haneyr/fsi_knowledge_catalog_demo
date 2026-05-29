#!/usr/bin/env python3
"""Unit tests for the region model helpers (issue #20)."""
import unittest

from common import entry_group_location, entry_type_location


class RegionModelTest(unittest.TestCase):
    def setUp(self):
        # Shape produced by common.load_config()
        self.cfg = {
            "project_id": "fsi-kc-demo-dev",
            "multi_region": "us",
            "location": "us-central1",
            "region": "us-central1",
        }

    def test_entry_groups_use_multi_region(self):
        # User entry groups must match the glossary/BigQuery region so links resolve.
        self.assertEqual(entry_group_location(self.cfg), "us")

    def test_entry_types_use_regional(self):
        # Entry/aspect types stay regional (no cross-region link constraints).
        self.assertEqual(entry_type_location(self.cfg), "us-central1")

    def test_entry_type_falls_back_to_region_when_no_location(self):
        cfg = {"multi_region": "us", "region": "us-central1"}
        self.assertEqual(entry_type_location(cfg), "us-central1")


if __name__ == "__main__":
    unittest.main()
