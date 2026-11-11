from text_cross8 import *
b6 = six_bucket_book()
def full(r, s):
    r = r.loc[s:].dropna(); ret = (np.exp(252 * r.mean()) - 1) * 100; vol = np.expm1(r).std(ddof=1) * np.sqrt(252) * 100; return round(float(ret / vol), 3), round(float(vol), 2)
print("six-bucket from 2012: EW", full(b6["EW PORT"], "2012-01-01"), "IV", full(b6["Inverse Vol"], "2012-01-01"))
b = bench_corr(b6["Skewness"].loc["2012-01-01":]); print("six-bucket Skewness bench from 2012", {k: round(v, 3) for k, v in b.items()})
bE6 = bench_corr(b6["EW PORT"].loc["2012-01-01":]); bI6 = bench_corr(b6["Inverse Vol"].loc["2012-01-01":]); print("six-bucket commodity index corr EW/IV from 2012", round(bE6["Commodity Index"], 3), round(bI6["Commodity Index"], 3))
