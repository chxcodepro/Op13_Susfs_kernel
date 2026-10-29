import base64
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

import verify_sukisu_uapi as compat


class UapiTests(unittest.TestCase):
    def test_builtin_and_release_headers(self):
        for version in (5, 6):
            for header in [
                f"DECLARE(__u32, KERNEL_SU_UAPI_VERSION, {version});",
                f"static const __u32 KERNEL_SU_UAPI_VERSION = {version};",
                f"#define KERNEL_SU_UAPI_VERSION {version}\n",
            ]:
                with self.subTest(header=header):
                    self.assertEqual(compat.parse_uapi_version(header), version)

    def test_comments_do_not_spoof_the_interface(self):
        header = "// KERNEL_SU_UAPI_VERSION = 5;\nDECLARE(__u32, KERNEL_SU_UAPI_VERSION, 2);"
        self.assertEqual(compat.parse_uapi_version(header), 2)

    def test_missing_or_ambiguous_version_fails(self):
        for source in ["", "// KERNEL_SU_UAPI_VERSION = 5;", "#define KERNEL_SU_UAPI_VERSION 0",
                       "KERNEL_SU_UAPI_VERSION = 2; KERNEL_SU_UAPI_VERSION = 5;"]:
            with self.subTest(source=source), self.assertRaises(ValueError):
                compat.parse_uapi_version(source)

    def test_real_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            kernel = Path(directory)
            (kernel / "include/uapi").mkdir(parents=True)
            (kernel / "include/uapi/supercall.h").write_text(
                "DECLARE(__u32, KERNEL_SU_UAPI_VERSION, 2);"
            )
            with patch.object(compat, "manager_uapi", return_value=5), \
                 self.assertRaisesRegex(ValueError, "driver=2, Manager v4.2.1=5"):
                compat.verify(kernel, "v4.2.1")

    def test_matching_pair_and_explicit_manual_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            kernel = Path(directory) / "kernel"
            (kernel / "include/uapi").mkdir(parents=True)
            (kernel / "include/uapi/supercall.h").write_text(
                "DECLARE(__u32, KERNEL_SU_UAPI_VERSION, 5);"
            )
            with patch.object(compat, "manager_uapi", return_value=5) as fetch:
                self.assertEqual(compat.verify(kernel, "v4.2.1")["manager_uapi"], 5)
                self.assertIsNone(compat.verify(kernel)["manager_uapi"])
                self.assertEqual(fetch.call_count, 1)

    def test_manual_version_checks_the_real_manager_interface(self):
        with tempfile.TemporaryDirectory() as directory:
            kernel = Path(directory) / "kernel"
            (kernel / "include/uapi").mkdir(parents=True)
            header = kernel / "include/uapi/supercall.h"
            with patch.object(compat, "manager_tag_for_version", return_value="v4.2.1-r2") as resolve, \
                 patch.object(compat, "manager_uapi", return_value=6):
                header.write_text("DECLARE(__u32, KERNEL_SU_UAPI_VERSION, 5);")
                with self.assertRaisesRegex(ValueError, "driver=5, Manager v4.2.1-r2=6"):
                    compat.verify(kernel, manager_version="41068")
                header.write_text("DECLARE(__u32, KERNEL_SU_UAPI_VERSION, 6);")
                report = compat.verify(kernel, manager_version="41068")
                self.assertEqual(report["mode"], "manual-checked")
                self.assertEqual(report["manager_tag"], "v4.2.1-r2")
                self.assertEqual(report["manager_version"], "41068")
                self.assertEqual(report["manager_uapi"], 6)
                resolve.assert_called_with("41068")

    def test_manual_release_resolution_skips_unreleased_and_missing_assets(self):
        release = {
            "tag_name": "v4.2.1-r2",
            "assets": [{"name": "SukiSU_v4.2.1-r2_41068-release.apk"}],
        }
        with patch.object(compat, "github_json", return_value=[
            dict(release, tag_name="draft", draft=True),
            dict(release, tag_name="preview", prerelease=True),
            {"tag_name": "tools", "assets": []},
            release,
        ]):
            self.assertEqual(compat.manager_tag_for_version("41068"), "v4.2.1-r2")
        with patch.object(compat, "github_json", return_value=[]), \
             self.assertRaisesRegex(ValueError, "No official stable Manager release"):
            compat.manager_tag_for_version("51068")

    def test_manual_release_resolution_paginates(self):
        release = {"tag_name": "v4.2.1", "assets": [{"name": "SukiSU_40994-release.apk"}]}
        with patch.object(compat, "github_json", side_effect=[
            [{"tag_name": "tools", "assets": []}] * 100,
            [release],
        ]) as fetch:
            self.assertEqual(compat.manager_tag_for_version("40994"), "v4.2.1")
            self.assertEqual(fetch.call_args_list[1].args[0], "releases?per_page=100&page=2")

    def test_invalid_manual_version_does_not_query_releases(self):
        with patch.object(compat, "github_json") as fetch:
            for version in ("auto", "41068;echo", "00000"):
                with self.subTest(version=version), self.assertRaises(ValueError):
                    compat.manager_tag_for_version(version)
            fetch.assert_not_called()

    def test_release_layout_and_bom(self):
        with tempfile.TemporaryDirectory() as directory:
            kernel = Path(directory) / "kernel"
            kernel.mkdir()
            (kernel.parent / "uapi").mkdir()
            (kernel.parent / "uapi/supercall.h").write_text(
                "static const __u32 KERNEL_SU_UAPI_VERSION = 5;", encoding="utf-8-sig"
            )
            self.assertEqual(compat.driver_uapi(kernel), 5)

    def test_legacy_manual_source_does_not_gain_auto_preconditions(self):
        with tempfile.TemporaryDirectory() as directory:
            kernel = Path(directory)
            report = compat.verify(kernel)
            self.assertIsNone(report["kernel_uapi"])
            self.assertEqual(report["mode"], "manual-unchecked")
            with patch.object(compat, "manager_uapi", return_value=5), \
                 self.assertRaises(ValueError):
                compat.verify(kernel, "v4.2.1")

    def test_manager_source_fetch_and_failure(self):
        source = b"static const __u32 KERNEL_SU_UAPI_VERSION = 5;"
        payload = json.dumps({"content": base64.b64encode(source).decode()}).encode()
        with patch.object(compat, "urlopen", return_value=io.BytesIO(payload)) as fetch:
            self.assertEqual(compat.manager_uapi("v4.2.1"), 5)
            self.assertIn("ref=v4.2.1", fetch.call_args.args[0].full_url)
        with patch.object(compat, "urlopen", side_effect=URLError("offline")), \
             self.assertRaises(URLError):
            compat.manager_uapi("v4.2.1")


if __name__ == "__main__":
    unittest.main()
