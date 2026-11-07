# SIGIL integrity boundary

This is a source repair of a legacy ledger. It does not establish that the library is deployed or that any agent system is operating correctly.

`audit_chain()` now reports `verdict: VALID | INVALID | UNCHECKABLE`. The compatibility `intact` field is respectively `true`, `false`, or `null`. Unavailable verification code or a public key, an unsupported algorithm, an incomplete scan and a missing/empty ledger cannot produce VALID. A detected bad signature or chain link remains INVALID even when other records could not be checked. `records` counts the inspected records; it is null when the source is missing. `verify_uncheckable`, `complete` and `reasons` expose the limits.

`sigil_ed25519.verify_result()` provides the same three states. `verify()` remains boolean and is true only for VALID. A caller-supplied public key must be selected independently; otherwise the verifier reads the configured public-key file. A public-key read never creates or reads a private key. A record's inline key is not trusted.

A configured signer must declare Ed25519 and return an Ed25519-shaped signature. If it raises or returns a malformed signature, emission raises; there is no HMAC fallback labelled Ed25519. Explicit no-signer operation retains the existing local HMAC mode. The legacy singleton's automatic signer discovery can still choose that mode when signing is unavailable; it must not be interpreted as an Ed25519 availability guarantee.

Emission returns and advances its in-memory chain only after append, flush and fsync succeed. After a persistence exception, some bytes may already be on disk, so the bus refuses further emissions until the caller reconciles the ledger and creates a new instance. It neither returns a successful receipt nor claims the append definitely did not happen. An unreadable or malformed existing head does not silently restart at genesis. Secondary audit logging remains best-effort after the ledger write.

Remaining limits deliberately not redesigned here:

- One writer only; no process/thread coordination or transaction protocol.
- The current SIGIL digest is truncated by the protocol. Signatures cover that digest plus the previous signature, not timestamps, glosses, algorithm tags, or other record metadata. Full-envelope signing requires a versioned migration.
- No historical trusted-key registry or key-rotation epoch is bound into each record. A mismatch is relative to the selected key, not a finding of forgery. The configured local key file is not an authenticated external identity.
- Legacy development HMAC-key defaults are unchanged; HMAC is not publicly verifiable identity.
- No execution-effect proof, human-authority binding, scientific validity, or Council measurement admission follows from these signatures.

Validation: `python -m unittest discover -s tests -p test_sigil_integrity.py -v`. Tests use temporary ledgers and ephemeral keys. The dedicated SIGIL integrity workflow does not swallow failures; the repository's older broad workflows still contain `|| true` and are not evidence that unrelated tests passed.
