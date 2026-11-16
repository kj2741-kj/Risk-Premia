"""Portfolio construction with product-level netting of the 5 bps cost (2026-11-15), shared by analyze_v3.py, classical_portfolio.py and rankings_page_v3.py.
Rules in research/netting.py. Strategy (style) rows stay on their own cost; every row that combines strategies is netted at product level with the
weights of its own construction (EW 1/5; Inverse Vol: the schedule solved on the standalone style series, mapped to product dates by the next common date).
Inputs: products_nets.pkl and products_pos.pkl of the tag (compute_products_v3.py)."""
import pickle
import sys

sys.path.insert(0, "research"); sys.path.insert(0, "research/configs"); sys.path.insert(0, "scripts")
from engine import combine_returns
from cross_asset_engine import combine_cross_asset
from netting import netted, inverse_vol_weights, combine_with_weights

TC_BPS = 5        # compute_products_v3.TC


class Netted:
    def __init__(self, out_dir, styles):
        self.nets, self.meta = pickle.load(open(out_dir / "products_nets.pkl", "rb"))
        self.pos, self.ph = pickle.load(open(out_dir / "products_pos.pkl", "rb"))
        assert set(self.pos) == set(self.nets), "products_pos.pkl and products_nets.pkl differ: rerun compute_products_v3.py"
        self.styles = tuple(styles)

    def adj(self, m, a=None):
        """Sleeves of product m netted for weights a (DataFrame with style columns) or equal weights."""
        return netted(self.nets[m], self.pos[m], self.ph[m], TC_BPS, a)

    def style_lines(self, members, sleeves_of):
        out = {}
        for st in self.styles:
            ser = [sleeves_of(m)[st] for m in members if not self.nets[m][st].empty]
            out[st] = combine_cross_asset(ser) if len(ser) > 1 else ser[0]
        return out

    def bucket(self, members):
        """-> standalone style lines, netted EW PORT, netted Inverse Vol, netted-EW style lines (for By Style), IV weight schedule."""
        styles = self.style_lines(members, lambda m: self.nets[m])
        ew_lines = self.style_lines(members, lambda m: self.adj(m))
        ew = combine_returns(list(ew_lines.values()), "equal_weight")
        w = inverse_vol_weights(list(styles.values()), 63)
        a = w.set_axis(list(styles), axis=1)
        iv_lines = self.style_lines(members, lambda m: self.adj(m, a))
        iv = combine_with_weights(list(iv_lines.values()), w)
        return dict(styles=styles, ew=ew, iv=iv, ew_lines=ew_lines, w=w)

    def product_ports(self, m):
        """Single product, five sleeves: netted EW and netted Inverse Vol (the rankings page's EW-5 / IV-5)."""
        lst = [self.nets[m][s] for s in self.styles]
        ew = combine_returns(list(self.adj(m).values()), "equal_weight")
        w = inverse_vol_weights(lst, 63)
        iv_s = self.adj(m, w.set_axis(list(self.styles), axis=1))
        iv = combine_with_weights([iv_s[s] for s in self.styles], w)
        return ew, iv

    def bystyle(self, buckets, acs, align_intersection):
        """By Style book: style rows standalone (each style equal-weighted across buckets); EW PORT and Inverse Vol netted."""
        keys = list(buckets)
        srows = {}
        for st in self.styles:
            al, _ = align_intersection([acs[k]["styles"][st] for k in keys])
            srows[st] = combine_returns(al, "equal_weight")
        ew_rows = {}
        for st in self.styles:
            al, _ = align_intersection([acs[k]["ew_lines"][st] for k in keys])
            ew_rows[st] = combine_returns(al, "equal_weight")
        u = inverse_vol_weights(list(srows.values()), 63)
        a = u.set_axis(list(self.styles), axis=1)
        iv_lines = {k: self.style_lines(buckets[k][1], lambda m: self.adj(m, a)) for k in keys}
        iv_rows = {}
        for st in self.styles:
            al, _ = align_intersection([iv_lines[k][st] for k in keys])
            iv_rows[st] = combine_returns(al, "equal_weight")
        return srows, combine_returns(list(ew_rows.values()), "equal_weight"), combine_with_weights(list(iv_rows.values()), u)
