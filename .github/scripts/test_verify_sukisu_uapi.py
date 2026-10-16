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
        for header in [
            "DECLARE(__u32, KERNEL_SU_UAPI_VERSION, 5);",
            "static const __u32 KERNEL_SU_UAPI_VERSION = 5;",
            "#define KERNEL_SU_UAPI_VERSION 5\n",
        ]:
            with self.subTest(header=header):
                self.assertEqual(compat.parse_uapi_version(header), 5)

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
