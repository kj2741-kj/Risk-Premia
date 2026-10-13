"""List every code-asserted claim in the v4 text modules that no longer holds under the current per-product net returns (collects failures instead of stopping)."""
import sys, os, importlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import facts
FAILS = []
def collector(cond, msg):
    if not cond: FAILS.append(msg)
facts.chk = collector
for name in ("facts2", "facts3"):
    if name in sys.modules: del sys.modules[name]
res = {}
for mod, fns in (("text_front", ("front",)), ("text_metals", ("metals",)), ("text_energy", ("energy",)), ("text_precious", ("precious",)),
                 ("text_ngl", ("ngl",)), ("text_agri", ("agri",)), ("text_corr", ("correlation", "crosscommodity")), ("text_appendix", ("appendix", "verification"))):
    m = importlib.import_module(mod)
    for fn in fns:
        before = len(FAILS)
        try:
            getattr(m, fn)()
        except Exception as e:
            FAILS.append(f"[{mod}.{fn}] raised {type(e).__name__}: {str(e)[:120]}")
        res[f"{mod}.{fn}"] = FAILS[before:]
for k, v in res.items():
    print(k, "->", len(v), "failed")
    for x in v: print("    -", x)
