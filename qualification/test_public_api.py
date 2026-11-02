"""Regression tests for the narrow approved public-surface addition."""
import csv
import tempfile
import unittest
from pathlib import Path

import check_public_api as public_api


class ApprovedPublicAdditionTests(unittest.TestCase):
    def test_legacy_context_api_and_runner_method_are_in_the_native_export(self):
        from tools.export_xml import active_objects
        objects = {item.name: item for item in active_objects()}
        self.assertIn('CONFIGURE_LEGACY_RUN', set(objects))
        self.assertIn('ConfigureLegacyRun', {method.name for method in objects['FB_coUnitRunner'].members})

    def setUp(self):
        with public_api.INVENTORY.open(encoding='utf-8-sig', newline='') as stream:
            self.row = next(row for row in csv.DictReader(stream) if row['symbol'] == 'GVL_Param_coUnit')
        self.baseline_file = public_api.BASELINE / self.row['source_path']
        self.candidate_file = public_api.CANDIDATE / self.row['source_path']
        self.candidate_text = self.candidate_file.read_text(encoding='utf-8-sig')
        self.approved = 'DiagnosticJsonEnablePublish : BOOL := FALSE;'

    def _check_candidate_text(self, text):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate_file = root / self.row['source_path']
            candidate_file.parent.mkdir(parents=True)
            candidate_file.write_text(text, encoding='utf-8')
            inventory = root / 'inventory.csv'
            with inventory.open('w', encoding='utf-8', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=('symbol', 'kind', 'source_path'))
                writer.writeheader()
                writer.writerow({key: self.row[key] for key in ('symbol', 'kind', 'source_path')})
            return public_api.check(public_api.BASELINE, root, inventory)

    def test_actual_candidate_passes_with_the_exact_approved_default_off_setting(self):
        self.assertEqual(self.candidate_text.count(self.approved), 1)
        self.assertEqual(public_api.check(public_api.BASELINE, public_api.CANDIDATE), [])

    def test_wrong_name_type_default_duplicate_and_other_drift_are_rejected(self):
        self.assertIn(self.approved, self.candidate_text)
        invalid = {
            'wrong name': self.candidate_text.replace(self.approved, 'DiagnosticJsonEnablePublishX : BOOL := FALSE;'),
            'wrong type': self.candidate_text.replace(self.approved, 'DiagnosticJsonEnablePublish : UDINT := FALSE;'),
            'wrong default': self.candidate_text.replace(self.approved, 'DiagnosticJsonEnablePublish : BOOL := TRUE;'),
            'duplicate': self.candidate_text.replace(self.approved, self.approved + '\n    ' + self.approved),
            'other constant drift': self.candidate_text.replace(
                'xUnitEnablePublish : BOOL := TRUE;', 'xUnitEnablePublish : BOOL := FALSE;'
            ),
        }
        for label, candidate in invalid.items():
            with self.subTest(label=label):
                self.assertNotEqual(candidate, self.candidate_text)
                self.assertTrue(self._check_candidate_text(candidate))


if __name__ == '__main__':
    unittest.main()
