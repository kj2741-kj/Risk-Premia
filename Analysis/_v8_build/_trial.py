import os; os.environ["CHK_SOFT"]="1"
import facts
from text_petroleum import petroleum
from text_front8 import key_findings, liquidity_paragraph
from text_cross8 import corr8, cross8
for f in (petroleum,liquidity_paragraph,corr8,cross8):
    try: f()
    except TypeError as e: print("skip",f.__name__,e)
    except Exception as e: print("ERR",f.__name__,type(e).__name__,str(e)[:200])
print("SOFT FAILS:"); [print(" -",m) for m in facts.SOFT_FAILS]
