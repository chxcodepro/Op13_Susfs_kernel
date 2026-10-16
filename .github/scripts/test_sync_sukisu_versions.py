import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

import sync_sukisu_versions as sync


def release(*names, **fields):
    return dict(tag_name="v4.2.1", assets=[{"name": name} for name in names], **fields)


class ReleaseVersionTests(unittest.TestCase):
    def test_official_apk_wins_over_other_assets(self):
        payload = release("Other_99999-release.apk", "SukiSU_v4.2.1_40994-release.apk")
        self.assertEqual(sync.release_version(payload), "40994")

    def test_release_apk_wins_over_fallback(self):
        payload = release("SukiSU_88888-debug.apk", "SukiSU_v4.2.1_40994-release.apk")
        self.assertEqual(sync.release_version(payload), "40994")

    def test_fallback_matches_build_resolver(self):
        self.assertEqual(sync.release_version(release("Manager_12345_40994.apk")), "40994")

    def test_invalid_releases_fail(self):
        for payload in [
            release("SukiSU_40994-release.apk", draft=True),
            release("SukiSU_40994-release.apk", prerelease=True),
            release("source.zip"),
            release("SukiSU_00000-release.apk"),
            {"assets": [{"name": "SukiSU_40994-release.apk"}]},
        ]:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                sync.release_version(payload)


class DropdownTests(unittest.TestCase):
    def setUp(self):
        self.source = sync.WORKFLOW.read_bytes().decode("utf-8").replace("\r\n", "\n")

    def test_latest_choice_and_compatibility_values(self):
        updated = sync.update_choices(self.source, "41050")
        self.assertIn('          - "41050"', updated)
        self.assertIn('          - "40900"', updated)
        self.assertIn('          - "40796"', updated)
        self.assertIn('        default: "auto"', updated)
        self.assertIn("当前已同步：41050", updated)
        self.assertNotIn("latest synced:", updated)
        self.assertEqual(sync.update_choices(updated, "41050"), updated)

    def test_next_release_replaces_previous_latest(self):
        updated = sync.update_choices(sync.update_choices(self.source, "41050"), "41100")
        self.assertIn('          - "41100"', updated)
        self.assertNotIn('          - "41050"', updated)

    def test_compatibility_version_is_not_duplicated(self):
        updated = sync.update_choices(self.source, "40900")
        self.assertEqual(updated.count('          - "40900"'), 1)

    def test_unrelated_content_and_line_endings_are_preserved(self):
        for newline in ["\n", "\r\n"]:
            source = self.source.replace("\r\n", "\n").replace("\n", newline)
            updated = sync.update_choices(source, "41050")
            before, rest = source.split("      sukisu_driver_version:", 1)
            _, after = rest.split("      kpm_enable:", 1)
            self.assertTrue(updated.startswith(before + "      sukisu_driver_version:"))
            self.assertTrue(updated.endswith("      kpm_enable:" + after))
            self.assertEqual(updated.count("\r\n"), updated.count("\n") if newline == "\r\n" else 0)

    def test_bad_layout_or_version_leaves_file_unchanged(self):
        for source in [
            self.source.replace("      sukisu_driver_version:", "      renamed_input:"),
            self.source.replace("        options:\n          - auto", "        options: [auto]"),
            self.source.replace("        type: choice", "        type: string"),
        ]:
            with self.subTest(source=source[:80]), self.assertRaises(ValueError):
                sync.update_choices(source.replace("\r\n", "\n"), "41050")
        with self.assertRaises(ValueError):
            sync.update_choices(self.source, "${{ github.token }}")

    def test_check_mode_does_not_write(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "workflow.yml"
            path.write_bytes(self.source.encode("utf-8"))
            self.assertEqual(sync.sync_workflow(path, release("SukiSU_41050-release.apk"), True), ("41050", True))
            self.assertEqual(path.read_bytes(), self.source.encode("utf-8"))
            self.assertEqual(sync.sync_workflow(path, release("SukiSU_41050-release.apk")), ("41050", True))
            self.assertEqual(sync.sync_workflow(path, release("SukiSU_41050-release.apk")), ("41050", False))
            original = path.read_bytes()
            with self.assertRaises(ValueError):
                sync.sync_workflow(path, release("source.zip"))
            self.assertEqual(path.read_bytes(), original)

    def test_api_failure_does_not_update_workflow(self):
        with patch.object(sync, "latest_release", side_effect=URLError("offline")), \
             patch.object(sync, "sync_workflow") as writer, \
             patch("sys.argv", ["sync_sukisu_versions.py"]), \
             contextlib.redirect_stderr(io.StringIO()) as errors:
            self.assertEqual(sync.main(), 1)
            writer.assert_not_called()
            self.assertIn("offline", errors.getvalue())

    def test_action_outputs_report_changed_then_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            workflow = Path(directory) / "workflow.yml"
            output = Path(directory) / "outputs"
            workflow.write_bytes(self.source.encode("utf-8"))
            with patch.object(sync, "WORKFLOW", workflow), \
                 patch.object(sync, "latest_release", return_value=release("SukiSU_41050-release.apk")), \
                 patch.dict("os.environ", {"GITHUB_OUTPUT": str(output)}), \
                 patch("sys.argv", ["sync_sukisu_versions.py"]), \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(sync.main(), 0)
                self.assertEqual(sync.main(), 0)
            self.assertEqual(output.read_text(), "version=41050\nchanged=true\nversion=41050\nchanged=false\n")


if __name__ == "__main__":
    unittest.main()
