"""SOV3 venv shim — this VM's /usr/bin/python3.11 is 3.11.0rc1, which lacks
sys.get_int_max_str_digits / set_int_max_str_digits (those landed in 3.11.0 FINAL).
torch 2.12's _dynamo polyfills require them WITH EXACT signatures, or torch import
crashes (which took SOV3 down on restart). Inject correct-signature defaults so torch
imports cleanly. REMOVE this once the interpreter is upgraded to 3.11-final/3.12 or the
venv is rebuilt on python3.10 (which already has these).
"""
import sys as _sys

if not hasattr(_sys, "get_int_max_str_digits"):
    def get_int_max_str_digits() -> int:          # matches torch's polyfill signature
        return 4300                                # CPython default int<->str conversion limit

    def set_int_max_str_digits(maxdigits: int) -> None:
        return None

    _sys.get_int_max_str_digits = get_int_max_str_digits
    _sys.set_int_max_str_digits = set_int_max_str_digits
