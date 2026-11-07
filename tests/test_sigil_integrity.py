"""Failure-path tests use temporary ledgers and ephemeral keys only."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "multi_agent"))
import sigil_bus as bus_module
import sigil_ed25519 as ed


class SigilIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.ledger = self.root / "ledger.jsonl"
        self.key_patch = patch.object(ed, "_PUB", str(self.root / "public.hex"))
        self.key_patch.start()
        self.addCleanup(self.key_patch.stop)
        self.bus = bus_module.SigilBus(key="test-only", ledger_path=str(self.ledger))

    def ephemeral_signer(self):
        self.assertTrue(ed.available(), "cryptography is required for the integrity gate")
        key = ed.Ed25519PrivateKey.generate()
        (self.root / "public.hex").write_text(key.public_key().public_bytes_raw().hex())
        def sign(message):
            return key.sign(message.encode()).hex()
        sign.alg = "ed25519"
        return sign

    def test_hmac_chain_and_tamper(self):
        self.bus.alert("info", "first")
        self.bus.alert("info", "second")
        self.assertEqual(self.bus.audit_chain()["verdict"], "VALID")
        records = [json.loads(x) for x in self.ledger.read_text().splitlines()]
        records[1]["line"] += "tampered"
        self.ledger.write_text("\n".join(json.dumps(x) for x in records) + "\n")
        self.assertEqual(self.bus.audit_chain()["verdict"], "INVALID")

    def test_ed25519_valid_then_missing_library_is_uncheckable(self):
        self.bus._signer = self.ephemeral_signer()
        self.bus.alert("info", "signed")
        self.assertEqual(self.bus.audit_chain()["verdict"], "VALID")
        with patch.object(ed, "_HAVE", False):
            report = self.bus.audit_chain()
        self.assertEqual(report["verdict"], "UNCHECKABLE")
        self.assertIsNone(report["intact"])
        self.assertEqual(report["verify_fail"], 0)
        self.assertEqual(report["verify_uncheckable"], 1)

    def test_missing_module_and_unknown_algorithm_are_uncheckable(self):
        self.bus._signer = self.ephemeral_signer()
        self.bus.alert("info", "signed")
        with patch.dict(sys.modules, {"sigil_ed25519": None}):
            self.assertEqual(self.bus.audit_chain()["verdict"], "UNCHECKABLE")
        rec = json.loads(self.ledger.read_text())
        rec["alg"] = "unimplemented"
        self.ledger.write_text(json.dumps(rec) + "\n")
        self.assertEqual(self.bus.audit_chain()["verdict"], "UNCHECKABLE")

    def test_missing_key_does_not_create_key_and_inline_key_is_not_trusted(self):
        self.bus._signer = self.ephemeral_signer()
        self.bus.alert("info", "signed")
        rec = json.loads(self.ledger.read_text())
        rec["public_key"] = (self.root / "public.hex").read_text()
        self.ledger.write_text(json.dumps(rec) + "\n")
        (self.root / "public.hex").unlink()
        with patch.object(ed, "_load_or_create", side_effect=AssertionError("read created key")):
            self.assertIsNone(ed.public_key_hex())
            self.assertEqual(self.bus.audit_chain()["verdict"], "UNCHECKABLE")

    def test_malformed_key_uncheckable_bad_signature_invalid(self):
        signer = self.ephemeral_signer()
        signature = signer("message")
        self.assertEqual(ed.verify_result("message", signature)["verdict"], "VALID")
        self.assertEqual(ed.verify_result("other", signature)["verdict"], "INVALID")
        self.assertEqual(ed.verify_result("message", signature, "bad")["verdict"], "UNCHECKABLE")
        self.assertFalse(ed.verify("other", signature))

    def test_signer_failure_has_no_fallback_or_success_record(self):
        def failed(_):
            raise RuntimeError("test signer unavailable")
        failed.alg = "ed25519"
        self.bus._signer = failed
        with self.assertRaises(RuntimeError):
            self.bus.alert("info", "never written")
        self.assertFalse(self.ledger.exists())
        self.assertEqual(self.bus.recent(), [])
        self.assertEqual(self.bus._last_sig, bus_module._GENESIS)

    def test_undeclared_or_malformed_signer_output_is_rejected(self):
        def fake(_):
            return "0" * 64  # HMAC-shaped, not Ed25519
        self.bus._signer = fake
        with self.assertRaises(ValueError):
            self.bus.alert("info", "undeclared")
        fake.alg = "ed25519"
        with self.assertRaises(ValueError):
            self.bus.alert("info", "wrong length")
        self.assertFalse(self.ledger.exists())

    def test_failed_append_or_fsync_does_not_advance_memory_or_return_receipt(self):
        for boundary in ("append", "fsync"):
            with self.subTest(boundary=boundary):
                ledger = self.root / (boundary + ".jsonl")
                bus = bus_module.SigilBus(key="test", ledger_path=str(ledger))
                target = patch.object(bus, "_append_ledger", side_effect=OSError("disk failed")) if boundary == "append" else patch.object(bus_module.os, "fsync", side_effect=OSError("sync failed"))
                with target, self.assertRaises(OSError):
                    bus.alert("info", "uncertain persistence")
                self.assertEqual(bus.recent(), [])
                self.assertEqual(bus._last_sig, bus_module._GENESIS)
                with self.assertRaisesRegex(OSError, "reconcile"):
                    bus.alert("info", "retry refused")

    def test_missing_empty_and_truncated_scans_do_not_claim_valid(self):
        self.assertEqual(self.bus.audit_chain()["verdict"], "UNCHECKABLE")
        self.assertIsNone(self.bus.audit_chain()["records"])
        self.ledger.touch()
        self.assertEqual(self.bus.audit_chain()["verdict"], "UNCHECKABLE")
        self.bus.alert("info", "first")
        self.bus.alert("info", "second")
        result = self.bus.audit_chain(limit=1)
        self.assertEqual(result["records"], 1)
        self.assertFalse(result["complete"])
        self.assertEqual(result["verdict"], "UNCHECKABLE")

    def test_corrupt_existing_head_does_not_restart_at_genesis(self):
        self.ledger.write_text("not json\n")
        with self.assertRaises(OSError):
            bus_module.SigilBus(key="test", ledger_path=str(self.ledger))


if __name__ == "__main__":
    unittest.main()
