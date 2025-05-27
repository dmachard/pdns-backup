import unittest
import os
import tempfile
from prometheus_client.parser import text_string_to_metric_families

import pdnsbackup
from pdnsbackup import export

class args:
    e = None
    c = None
    v = False

zone_direct = { 'example.com': {
                        'stats': { 
                               "records": 10, "wilcards": 2, "delegations": 0,
                               "rrtypes": { "a": 1, "aaaa": 0, "txt": 0, "ptr": 0, "cname": 0,  
                                            "srv": 0, "mx": 0, "ns": 2, "others": 4},
                             } 
                        }
        }

class TestExportMetrics(unittest.TestCase):
    def test_export_metrics(self):
        cfg = pdnsbackup.setup_config(args, ignore_env=True)
        cfg["file-enabled"] = False
        cfg["metrics-enabled"] = True

        success = export.backup(cfg, zone_direct)
        self.assertTrue(success)

        self.assertTrue(os.path.exists(cfg["metrics-prom-file"]))


class TestMetricsContent(unittest.TestCase):
    def test_export_metrics_content(self):
        try:
            cfg = pdnsbackup.setup_config(args, ignore_env=True)
            cfg["file-enabled"] = False
            cfg["metrics-enabled"] = True

            success = export.backup(cfg, zone_direct)
            self.assertTrue(success)

            # Parse and validate metrics content
            with open(cfg["metrics-prom-file"], "r") as f:
                metrics_data = f.read()

            metrics = {
                metric.name: metric for family in text_string_to_metric_families(metrics_data) for metric in family.samples
            }

            # Validate specific metrics
            self.assertIn("pdnsbackup_status", metrics)
            self.assertIn("pdnsbackup_zones_total", metrics)
            self.assertIn("pdnsbackup_records_total", metrics)
            self.assertIn("pdnsbackup_rrtypes_total", metrics)
            self.assertIn("pdnsbackup_wildcards_total", metrics)
            self.assertIn("pdnsbackup_delegations_total", metrics)

            self.assertEqual(metrics["pdnsbackup_status"].value, 1.0)
            self.assertEqual(metrics["pdnsbackup_status"].labels["database"], "pdns")

            self.assertEqual(metrics["pdnsbackup_zones_total"].value, 1.0)
            self.assertEqual(metrics["pdnsbackup_zones_total"].labels["database"], "pdns")

            self.assertEqual(metrics["pdnsbackup_records_total"].value, 10.0)
            self.assertEqual(metrics["pdnsbackup_records_total"].labels["database"], "pdns")

            self.assertEqual(metrics["pdnsbackup_wildcards_total"].value, 2.0)
            self.assertEqual(metrics["pdnsbackup_wildcards_total"].labels["database"], "pdns")

            self.assertEqual(metrics["pdnsbackup_delegations_total"].value, 0.0)
            self.assertEqual(metrics["pdnsbackup_delegations_total"].labels["database"], "pdns")

            # Check the label "zone" exists and has the correct value
            record_metric = metrics["pdnsbackup_records_total"]
            self.assertEqual(record_metric.labels["zone"], "example.com")
            self.assertEqual(record_metric.labels["database"], "pdns")
            self.assertEqual(record_metric.value, 10.0)
        finally:
            # Cleanup temporary file
            if os.path.exists(cfg["metrics-prom-file"]):
                os.remove(cfg["metrics-prom-file"])