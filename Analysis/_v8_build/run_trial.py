"""Trial runner: python run_trial.py <module> <function>  (soft claims; prints every text block and the failing claims)."""
import os, sys
os.environ["CHK_SOFT"] = "1"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib
m = importlib.import_module(sys.argv[1]); out = getattr(m, sys.argv[2])()
import facts
for b in (out if isinstance(out, list) else [out]):
    print(b if not isinstance(b, tuple) else (b[0], b[1][:2000] if isinstance(b[1], str) else b[1:]))
    print()
print("FAILED CLAIMS:", facts.SOFT_FAILS)
