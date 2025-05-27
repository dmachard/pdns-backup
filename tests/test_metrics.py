import unittest
import os
import tempfile
from prometheus_client.parser import text_string_to_metric_families
from ..export import export_metrics

# filepath: /home/denis/Documents/Lab/pdns-backup/tests/test_export_metrics.py

class TestExportMetricsContent(unittest.TestCase):
    def test_export_metrics_content(self):
        # Create a temporary file for metrics
        with tempfile.NamedTemporaryFile(delete=False) as temp_metrics_file:
            metrics_file_path = temp_metrics_file.name

        try:
            # Configuration for metrics
            cfg = {
                "metrics-prom-file": metrics_file_path,
            }

            # Sample zones data
            zones = {
                "example.com": {
                    "stats": {
                        "records": 10,
                        "wilcards": 2,
                        "delegations": 0,
                        "rrtypes": {
                            "a": 1,
                            "aaaa": 0,
                            "txt": 0,
                            "ptr": 0,
                            "cname": 0,
                            "srv": 0,
                            "mx": 0,
                            "ns": 2,
                            "others": 4,
                        },
                    }
                }
            }

            # Call export_metrics
            status = True
            result = export_metrics(cfg, zones, status)
            self.assertTrue(result)

            # Parse and validate metrics content
            with open(metrics_file_path, "r") as f:
                metrics_data = f.read()

            metrics = {
                metric.name: metric for family in text_string_to_metric_families(metrics_data) for metric in family.samples
            }

            # Validate specific metrics
            self.assertIn("pdnsbackup_status", metrics)
            self.assertIn("pdnsbackup_zones_total", metrics)
            self.assertIn("pdnsbackup_records_total", metrics)

            self.assertEqual(metrics["pdnsbackup_status"].value, 1.0)
            self.assertEqual(metrics["pdnsbackup_zones_total"].value, 1.0)
            self.assertEqual(metrics["pdnsbackup_records_total"].value, 10.0)

        finally:
            # Cleanup temporary file
            if os.path.exists(metrics_file_path):
                os.remove(metrics_file_path)