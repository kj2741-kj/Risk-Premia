"""Paper Section 5 (Discussion) and Section 7 (Conclusion). Every number comes from the fact functions; every qualitative claim is wrapped in chk()."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import warnings
warnings.filterwarnings("ignore")
from facts3 import *

# --- number format of the paper: hyphen as the minus sign, no plus signs
def I(x):
    return "0.00" if abs(round(x, 2)) == 0 else f"{x:.2f}"


def N(x, d=2):
    return f"{0:.{d}f}" if abs(round(x, d)) == 0 else f"{x:.{d}f}"


def R(x):
    return "0.0%" if abs(round(x, 1)) == 0 else f"{x:.1f}%"



CL = ["metals", "energy", "ngl", "precious", "agri"]
_F = {}


def S(x, d=2):
    """Unsigned for positive values, ASCII hyphen for negative ones."""
    return I(x).lstrip("+") if d == 2 else (f"{x:.{d}f}")


def pc(x, d=0):
    return f"{x:.{d}f}%"


def facts():
    if _F:
        return _F
    F = _F
    F["ir"] = {(v, k, w): st(v, k, w)["ir"] for v in CL for k in SLEEVES + ["EW PORT", "Inverse Vol"] for w in ("full", "p1", "p2", "p3")}
    F["vol"] = {(v, k): st(v, k)["vol"] for v in CL for k in ("EW PORT", "Inverse Vol")}
    # sleeves positive in every subperiod
    allpos = {(v, k) for v in CL for k in SLEEVES if all(F["ir"][(v, k, w)] > 0 for w in ("p1", "p2", "p3"))}
    chk(allpos == {("ngl", "Momentum"), ("ngl", "Carry"), ("ngl", "CarryMom"), ("energy", "Momentum"), ("energy", "Carry"), ("energy", "CarryMom"), ("metals", "Value")},
        f"sleeves positive in every subperiod: {sorted(allpos)}")
    # yearly breadth
    F["ypos"] = {(v, k): (int((yearly_log(CS[v][k]) > 0).sum()), len(yearly_log(CS[v][k]))) for v in ("ngl", "energy") for k in ("Momentum", "Carry", "CarryMom")}
    # weakest product
    allmins = {(c, k): min(pst(c, q, k)["ir"] for q in PRODUCTS[c]) for c in CL for k in SLEEVES}
    chk(max(allmins, key=allmins.get) == ("ngl", "Momentum"), "NGL Momentum has the highest weakest-product IR")
    F["ngl_mom_min"] = allmins[("ngl", "Momentum")]
    # energy momentum concentration
    ms = CS["energy"]["Momentum"].loc["2012-01-01":].dropna(); yl = yearly_log(ms); tot = ms.sum()
    F["en_share4"] = yl.loc[[2014, 2015, 2020, 2021]].sum() / tot * 100
    F["en_share26"] = ms.loc["2026-01-01":].sum() / tot * 100
    chk(round(F["en_share4"]) == 95 and round(F["en_share26"]) == 23 and F["en_share4"] + F["en_share26"] > 100, "Energy Momentum concentration")
    # NGL seasonal slope
    from engine import _carry_base
    import importlib as _il
    ng = _il.import_module("ngl")
    sl = pd.concat([_carry_base(ng.load_curve(p_), "F2", "F4").loc["2012-01-01":].dropna() for p_ in PRODUCTS["ngl"]])
    m = sl.index.month
    F["f24w"] = 100 * sl[(m == 12) | (m <= 3)].mean(); F["f24s"] = 100 * sl[(m >= 6) & (m <= 9)].mean()
    chk(round(F["f24w"], 1) == 3.7 and round(F["f24s"], 1) == -1.7, "NGL F2-F4 seasonal slope")
    # oil prices 2026
    en = _il.import_module("energy")
    b = en.load_curve("Brent")["F1"]
    F["brent0"], F["brent1"] = float(b.loc["2026-02-27"]), float(b.loc["2026-03-31"])
    chk(round(F["brent0"]) == 72 and round(F["brent1"]) == 118, "Brent 2026 levels")
    F["cm_en"] = [st("energy", "CarryMom", w)["ir"] for w in ("p1", "p2", "p3")]
    return F


# ----------------------------------------------------------------------------- 5.1
def s51():
    F = facts(); ir = F["ir"]
    out = [("h2", "5.1 Why the premium is found in NGL and Energy")]
    P = out.append
    others = [ir[(v, k, "full")] for v in ("metals", "precious", "agri") for k in ("EW PORT", "Inverse Vol")]
    chk(ir[("ngl", "EW PORT", "full")] > ir[("energy", "EW PORT", "full")] and ir[("ngl", "Inverse Vol", "full")] > ir[("energy", "Inverse Vol", "full")] and max(others) < 0.1, "NGL ahead of Energy ahead of the rest")
    yp = F["ypos"]
    chk(yp[("ngl", "Momentum")][0] == 12 and yp[("energy", "Momentum")][0] == 9 and yp[("ngl", "Momentum")][1] == 15, "Momentum positive calendar years")
    P(("p", f"The result to be explained is narrow. In NGL and in Energy, Momentum, Carry and Carry-Momentum each earn a positive IR in every one of the three subperiods, and the only other sleeve to do so in any asset class is Value in Metals (Section 5.2). "
            f"NGL is the stronger of the two: its Equal Weight and Inverse Vol portfolios have IRs of {S(ir[('ngl','EW PORT','full')])} and {S(ir[('ngl','Inverse Vol','full')])}, against {S(ir[('energy','EW PORT','full')])} and {S(ir[('energy','Inverse Vol','full')])} in Energy, and none of the other three classes has a portfolio IR above {S(max(others))}. "
            f"Momentum earns a positive log return in {yp[('ngl','Momentum')][0]} of the {yp[('ngl','Momentum')][1]} calendar years in NGL and in {yp[('energy','Momentum')][0]} of the {yp[('energy','Momentum')][1]} in Energy (2026 is a partial year), so the NGL premium is also the more evenly spread through time. "
            f"The interpretations that follow ask what these two classes share that the other three do not."))
    cm = F["cm_en"]
    chk(ir[("energy", "CarryMom", "full")] == max(ir[("energy", k, "full")] for k in SLEEVES) and all(x > 0.6 for x in cm), "Energy Carry-Momentum strongest, positive each period")
    P(("p", f"The theory of storage ties the slope of the futures curve to the state of inventories (Section 1), and the three sleeves that pay in NGL and Energy are all read from that slope or from the price path that accompanies it. "
            f"Carry measures the slope against its own history and Carry-Momentum measures its change, and Carry-Momentum is the strongest Energy sleeve (IR {S(ir[('energy','CarryMom','full')])}; P1 {S(cm[0])}, P2 {S(cm[1])}, P3 {S(cm[2])}). "
            f"Virtual Barrels (2023, p. 83) describes carry as the prevailing state of inventories and momentum applied to carry as associated with expected changes in them, and argues (p. 87) that slow adjustment of oil supply and demand makes inventories, and therefore prices, trend. "
            f"The results are consistent with this account. They do not isolate it, because the signals are related by construction: winning contracts tend to be the backwardated ones, with low inventories and net short hedging (Fernandez-Perez, Fuertes and Miffre, 2021, citing Miffre and Rallis, 2007, and Gorton, Hayashi and Rouwenhorst, 2013)."))
    P(("p", "The hedging pressure hypothesis offers a second reading (Cootner, 1960; Hirshleifer, 1988, 1990). If producers and consumers lay off price risk in these markets and speculators are paid to absorb it, a long position in a backwardated contract earns the transfer, and the same curve-based signals would again be positive. "
            "Virtual Barrels (2023, p. 86) observes that in a diversified commodity risk premia book the largest share of the profit typically comes from energy futures, that the other sectors mainly diversify, and links this to the special role of storage and the behaviour of large market participants. "
            "A later chapter (p. 109) adds that such strategies have proven to work better for harder-to-store energy commodities. Our results fit these observations, since the premium in the trend and curve signals sits in the two energy-related classes. "
            "We measure neither storability, inventories nor the positions of any group of traders, so we cannot say which channel produces the premium, and the same results are consistent with both."))
    nm = F["ngl_mom_min"]
    P(("p", f"NGL deserves separate comment because it is both the strongest class and the one with the shortest liquid history. Momentum is positive in all four NGL products, and the weakest of them has an IR of {S(nm)}, the highest weakest-product IR of any sleeve in any asset class. "
            f"Over the sample the US moved from a market short of export outlets to one with large export capacity. Mont Belvieu propane traded at an average discount of $0.89 per gallon to international prices in 2012 because export terminals were at capacity (EIA), US propane exports averaged a record 1.8 million barrels a day in 2024 (EIA), "
            f"and ethane exports reached 492,000 barrels a day in 2024 against 65,000 in 2015 (OPIS, citing EIA). A market whose outlets expand year after year adjusts slowly to its surplus, the condition under which trends and persistent curve slopes are expected. "
            f"The F2-F4 slope, pooled over the four products, averages {N(F['f24w'],1)}% in December to March (backwardation) and {N(F['f24s'],1)}% in June to September (contango), a seasonal swing of the kind Carry and Carry-Momentum read. This context is consistent with the results; none of it was tested."))
    p1c, p1m = ir[("ngl", "Carry", "p1")], ir[("ngl", "Momentum", "p1")]
    P(("p", f"Two features of the NGL result call for caution. First, a slope that swings with the heating season can be forecast from the calendar alone, so NGL Carry may be reading the season as much as the state of inventories, and we have not separated the two. "
            f"Second, Bogorad (2025a) starts the backtest window in January 2015, the period in which ICE-listed NGL futures achieved sufficient liquidity for systematic trading following their introduction and growth in 2014 to 2015, and uses earlier data only to initialise signals. Our sample begins in 2012, and the NGL result is already strong in P1 (Momentum IR {S(p1m)}, Carry {S(p1c)}), "
            f"so part of the early premium may come from contracts that traded too thinly to be implemented at the 5 basis point cost we charge. We have no liquidity measure for the NGL contracts. Bogorad (2025a) also finds NGL Momentum profitable in both of its subsamples (an IR of 0.99 over its window), in line with our result, but reports NGL Carry as substantially weaker, "
            f"so the two studies agree on Momentum and differ on Carry, and the differences in contracts, tenors and window described in Section 4.1.4 limit what the comparison can show."))
    P(("p", f"In Energy the premium is also uneven through time. Calendar years 2014, 2015, 2020 and 2021 account for {F['en_share4']:.0f}% of the cumulative log return of the Momentum sleeve and the first nine months of 2026 for a further {F['en_share26']:.0f}%, so the remaining years net to a loss. "
            f"These are the fall in oil prices from 2014, the demand collapse of 2020, the recovery of 2021 and the war that began on 28 February 2026, during which Brent rose from ${F['brent0']:.0f} on 27 February to ${F['brent1']:.0f} on 31 March. "
            f"A premium that arrives in a few large moves is what trend-following on a storable commodity with inelastic supply and demand would produce, but it is also what a short sample dominated by a few events would produce, and our data cannot tell the two apart."))
    v_en = ir[("energy", "Value", "full")]
    chk(v_en < 0 and ir[("energy", "Skewness", "full")] > 0, "Energy Value negative, Skewness positive")
    P(("p", f"Three earlier studies bear on these results. Fernandez-Perez, Fuertes and Miffre (2021) form long-short portfolios across energy contracts each month and, unlike us, use data on the positions of hedgers and speculators, which we do not. "
            f"They find premia from term structure, hedging pressure, speculative pressure and momentum, which matches the sign of our Carry, Carry-Momentum and Momentum sleeves in Energy, and find the premia from value, liquidity and skewness statistically insignificant. "
            f"Our negative Energy Value sleeve (IR {S(v_en)}) does not contradict that finding. Our Energy Skewness sleeve (IR {S(ir[('energy','Skewness','full')])}) is positive, but the two Skewness results are not comparable because the rules are constructed differently, as Section 5.3 explains. Our rules also take one position per product, so they carry exposure to the direction of oil, while theirs are formed within the sector."))
    P(("p", "Bogorad (2025a) reports that some premia have weakened in the traditional benchmark contracts while others persist in newly liquid markets, NGL among them, and that simple aggregation of low-correlated signals works well. Our ranking of the classes is of the same kind, and the evidence on aggregation is taken up in Section 5.4. "
            "Fan, Li, Qiao and Zhang (2026) find that the predictive power for commodity returns is spread across inventory, hedging and liquidity channels whose weights change over time, with no single theory dominant. "
            "Our design cannot estimate such weights. Sleeves that share a root pay together in two classes and in every subperiod, which is what one channel would produce and also what several channels acting together would produce. "
            "The methods differ as well: they forecast returns with 81 variables, while we apply fixed rules, so our evidence neither supports nor contradicts their finding that the weights vary."))
    return out


# ----------------------------------------------------------------------------- 5.2
def s52():
    F = facts(); ir = F["ir"]
    import importlib as _il
    out = [("h2", "5.2 Why not Metals, Precious Metals and Agriculture")]
    P = out.append
    sl = {p: slope_stats("metals", p) for p in PRODUCTS["metals"]}
    cp1 = {p: pst("metals", p, "Carry", "p1")["ir"] for p in PRODUCTS["metals"]}
    chk(min(cp1[p] for p in ("Aluminium", "Zinc", "Lead")) > 0.3 and cp1["Copper"] < 0, "metals Carry P1")
    chk(max(sl[p]["p1"][1] for p in ("Aluminium", "Zinc", "Lead")) < 5 and all(sl[p]["p1"][0] < -1 for p in ("Aluminium", "Zinc", "Lead")), "metals P1 contango")
    mc = {k: [ir[("metals", k, w)] for w in ("p1", "p2", "p3")] for k in SLEEVES}
    chk(mc["Momentum"][0] < 0 and mc["Momentum"][2] < 0 and mc["Carry"][0] > 0.3 and abs(mc["Carry"][1]) < 0.05 and mc["Carry"][2] <= 0 and mc["CarryMom"][0] > 0.5 and mc["CarryMom"][1] < 0 and mc["CarryMom"][2] < 0 and all(x > 0 for x in mc["Value"]), "metals sleeve pattern")
    chk(ir[("metals", "EW PORT", "full")] < 0 and ir[("metals", "Inverse Vol", "full")] < 0.1 and ir[("metals", "Value", "full")] > 0.3, "metals portfolios below Value")
    mm = _il.import_module("metals")
    al = mm.load_curve("Aluminium")["F1"]; zn = mm.load_curve("Zinc")["F1"]
    chk(round(al.loc["2022-03-04"]) == 3876 and al.idxmax() == pd.Timestamp("2022-03-04") and round(al.loc["2023-12-11"]) == 2076 and round(zn.loc["2022-04-19"]) == 4523 and round(zn.loc["2023-05-31"]) == 2240, "metals price levels")
    vp3 = {p: pst("metals", p, "Value", "p3")["ir"] for p in PRODUCTS["metals"]}
    chk(vp3["Aluminium"] > 0.3 and vp3["Zinc"] > 0.3 and vp3["Lead"] > 0.3, "metals Value P3 by metal")
    P(("p", f"The same signals do not pay in the other three asset classes, and the explanations again are interpretations consistent with the results. Metals has one sleeve with a clear edge, Value (IR {S(ir[('metals','Value','full')])}), which is positive in every subperiod (P1 {S(mc['Value'][0])}, P2 {S(mc['Value'][1])}, P3 {S(mc['Value'][2])}). "
            f"Momentum is negative (IR {S(ir[('metals','Momentum','full')])}), and Carry and Carry-Momentum are positive only in P1 (IR {S(mc['Carry'][0])} and {S(mc['CarryMom'][0])}), against {S(mc['Carry'][1])} and {S(mc['CarryMom'][1])} in P2 and {S(mc['Carry'][2])} and {S(mc['CarryMom'][2])} in P3. "
            f"The P1 Carry premium comes from Aluminium, Zinc and Lead (IR {S(cp1['Aluminium'])}, {S(cp1['Zinc'])} and {S(cp1['Lead'])}), whose curves sat in persistent contango, with average F1-F13 slopes of {N(sl['Aluminium']['p1'][0],1)}%, {N(sl['Zinc']['p1'][0],1)}% and {N(sl['Lead']['p1'][0],1)}%. "
            f"Those were the years of large LME stocks, aluminium financing deals and warehouse queues of more than two years (Reuters; LME), conditions in which an overhang of stocks, and not scarcity, set the shape of the curve. Under that reading the storage channel is at work, but the curve describes a surplus that financing kept off the market, which is consistent with the premium fading as the contango eased."))
    P(("p", f"The metals that spiked in 2021 and 2022 then reversed sharply, a move that a trend signal cannot avoid and from which a reversion signal can profit: Aluminium peaked at ${al.loc['2022-03-04']:,.0f} on 4 March 2022 in our series and stood at ${al.loc['2023-12-11']:,.0f} in December 2023, and Zinc fell from ${zn.loc['2022-04-19']:,.0f} in April 2022 to ${zn.loc['2023-05-31']:,.0f} in May 2023. "
            f"Value in P3 comes from these metals (IR {S(vp3['Aluminium'])} in Aluminium, {S(vp3['Zinc'])} in Zinc and {S(vp3['Lead'])} in Lead), while Momentum loses in P3 (IR {S(mc['Momentum'][2])}). "
            f"Industrial metals are priced off a global activity cycle and off inventory and financing conditions that can change within months, and in this sample the large moves of 2021 and 2022 reverted instead of persisting. This is consistent with the absence of a trend and curve premium. "
            f"It also accounts for the portfolios doing worse than Value alone (Equal Weight {S(ir[('metals','EW PORT','full')])}, Inverse Vol {S(ir[('metals','Inverse Vol','full')])}): blending four sleeves with little or no edge dilutes the one that works."))
    ry = real_yield_stats()
    chk(abs(round(ry["full"]["corr"], 2) + 0.39) < 0.006 and abs(round(ry["p2"]["corr"], 2) + 0.64) < 0.006 and abs(round(ry["p3"]["corr"], 2) + 0.24) < 0.006 and round(ry["p3"]["avg"], 2) == 1.60 and round(ry["p2"]["avg"], 2) == 0.03, "real yields")
    gs = slope_stats("precious", "Gold", "F1", "F7")
    chk([round(gs[w][0], 1) for w in ("p3", "p2", "p1")] == [-4.5, -1.8, -0.6], "gold slope")
    pmx = {k: [ir[("precious", k, w)] for w in ("p1", "p2", "p3")] for k in SLEEVES}
    chk(all(ir[("precious", k, "full")] < 0 for k in CORE) and ir[("precious", "EW PORT", "full")] < 0 and ir[("precious", "Inverse Vol", "full")] < 0, "precious all core and portfolios negative")
    gp = _il.import_module("precious").load_curve("Gold")["F1"]
    chk(round(gp.loc["2022-09-30"]) == 1662 and round(gp.loc["2025-12-31"]) == 4341, "gold levels")
    gv = yearly_log(nets()[("precious", "Gold")]["Value"]); gvp3 = pst("precious", "Gold", "Value", "p3")["ir"]
    chk(round(gvp3, 2) == -0.61 and round(gv.loc[2025], 2) == -0.45, "gold Value")
    P(("p", f"In Precious Metals no core sleeve has a positive full-sample IR (Momentum {S(ir[('precious','Momentum','full')])}, Carry {S(ir[('precious','Carry','full')])}, Carry-Momentum {S(ir[('precious','CarryMom','full')])}, Value {S(ir[('precious','Value','full')])}), and both portfolios are negative (Equal Weight {S(ir[('precious','EW PORT','full')])}, Inverse Vol {S(ir[('precious','Inverse Vol','full')])}). "
            f"Gold's price is closely tied to macro variables. The weekly correlation of gold returns with changes in the 10-year real yield (FRED series DFII10) is {N(ry['full']['corr'])} over the sample, {N(ry['p2']['corr'])} in P2 and {N(ry['p3']['corr'])} in P3, and expectations of currency debasement and demand for protection against tail risk may add to it. This is consistent with there being little in the metal's own price path or curve for a trend or slope signal to read. "
            f"The curve is also a financing curve. The 10-year real yield averaged {U(ry['p3']['avg'])}% in P3 against {U(ry['p2']['avg'])}% in P2, and Gold's F1-F7 slope averaged {N(gs['p3'][0],1)}% in P3 against {N(gs['p2'][0],1)}% in P2 and {N(gs['p1'][0],1)}% in P1. "
            f"A slope that mainly reflects the cost of financing stored metal says little about scarcity, which is consistent with Carry and Carry-Momentum finding no edge (P3 Carry-Momentum IR {S(pmx['CarryMom'][2])})."))
    P(("p", f"The structure of the market may matter as well. Gold producers hedge little, with a global hedge book of 218 tonnes in the third quarter of 2017 and under 200 tonnes by the end of 2024 (World Gold Council), so there are few commercial hedgers paying speculators to take their price risk, which is the transfer that the hedging pressure hypothesis describes. "
            f"Central banks bought 863 tonnes in 2025 against an annual average of 473 tonnes in 2010 to 2021 (World Gold Council), a source of demand outside producer and consumer hedging. Value is the sleeve that suffers: it shorts a metal trading more than 10% above its five-year average, and gold rose from ${gp.loc['2022-09-30']:,.0f} at the end of September 2022 to ${gp.loc['2025-12-31']:,.0f} at the end of 2025. "
            f"Gold Value lost {abs(gv.loc[2025]):.2f} in log return in 2025 alone and has a P3 IR of {S(gvp3)}. The data cannot separate the roles of real yields, official demand and the absence of hedgers; each is consistent with the results."))
    ag = {k: [ir[("agri", k, w)] for w in ("p1", "p2", "p3")] for k in SLEEVES}
    chk(all(ir[("agri", k, "full")] < 0 for k in ("Momentum", "CarryMom", "Value")) and abs(ir[("agri", "Carry", "full")]) < 0.05 and ir[("agri", "EW PORT", "full")] < 0 and ir[("agri", "Inverse Vol", "full")] < 0, "agri core")
    cof = pper("agri", "Coffee", "CarryMom")
    chk(round(cof[1], 2) == 0.88 and round(cof[2], 2) == -0.64, "Coffee swing")
    ax = _il.import_module("agri")
    cc = {p: ax.load_curve(p)["F1"] for p in ("Coffee", "Wheat", "Corn")}
    chk(abs(cc["Coffee"].loc["2021-07-26"] / cc["Coffee"].loc["2021-07-19"] - 1 - 0.34) < 0.005, "arabica +34%")
    chk(round(cc["Wheat"].loc["2022-03-07"] / 100, 2) == 14.25 and abs(cc["Wheat"].loc["2026-09-23"] / 100 - 7.085) < 1e-6 and True and round(cc["Coffee"].loc["2025-02-13"] / 100, 2) == 4.39 and round(cc["Coffee"].loc["2026-09-23"] / 100, 2) == 2.76, "agri levels")
    ex_cof = [p for p in PRODUCTS["agri"] if p != "Coffee"]
    xc = ew_intersection([nets()[("agri", p)]["CarryMom"] for p in ex_cof])
    chk(stats(xc, "p2")["ir"] < 0 < ag["CarryMom"][1], "Coffee is the swing")
    P(("p", f"Agriculture has no core sleeve with an edge: Momentum (IR {S(ir[('agri','Momentum','full')])}), Carry-Momentum ({S(ir[('agri','CarryMom','full')])}) and Value ({S(ir[('agri','Value','full')])}) are negative, Carry is flat ({S(ir[('agri','Carry','full')])}), and the portfolios are negative (Equal Weight {S(ir[('agri','EW PORT','full')])}, Inverse Vol {S(ir[('agri','Inverse Vol','full')])}). "
            f"The pattern is one of spikes followed by reversals driven by weather and war. Arabica coffee rose 34% in a week in July 2021 after Brazilian frosts (19 to 26 July in our series), and reached ${cc['Coffee'].loc['2025-02-13']/100:.2f} per pound on 13 February 2025 before falling to ${cc['Coffee'].loc['2026-09-23']/100:.2f} by 23 September 2026. "
            f"Wheat peaked at ${cc['Wheat'].loc['2022-03-07']/100:.2f} per bushel on 7 March 2022 after Russia's invasion of Ukraine and was $7.09 at the end of the sample. "
            f"Coffee is the swing in the curve signals: Carry-Momentum in Coffee has an IR of {S(cof[1])} in P2 and {S(cof[2])} in P3, and without Coffee the class Carry-Momentum sleeve is negative in P2. Trend and slope signals need persistence, and a price that jumps on a frost or a war and then retraces does not supply it."))
    P(("p", f"Virtual Barrels (2023, p. 88) makes a related point about distributions. It contrasts agricultural and other seasonal commodities, whose prices tend to have a larger upside tail, with oil, which tends to rise gradually and fall abruptly, and notes that the large periodic breakdowns of the oil market make a diversified momentum strategy highly desirable to financial investors. "
            f"Taken together, the contrast between the classes is consistent with a difference in how price changes arrive. In NGL and Energy, adjustment of supply and demand is slow and the curve carries the information that the signals read. In Metals, financing and activity cycles reverse quickly. In Precious Metals, macro variables and financing costs drive the price. "
            f"In Agriculture, weather and war produce jumps that the curve does not announce. These are readings of the pattern and not tests of it. In particular, we have no data on the positions of hedgers in any of the three classes, so the hedging pressure explanation remains untested here."))
    return out


# ----------------------------------------------------------------------------- 5.3
def _getD(suffix):
    import json
    t = open(os.path.join(REPO, "Analysis", f"Final_Research_Dashboard_2012{suffix}.html"), encoding="utf8").read()
    i = t.find("const D=") + 8
    return json.JSONDecoder().raw_decode(t[i:])[0]


def _vote_vs_sum():
    """Full-sample IRs of Carry and Carry-Momentum per class and of the five-class Equal Weight book under the earlier rule (sign of each pair's signal, flat when the pairs disagree)
    and under the adopted summed rule, both on the same imputed-price data (outputs/final_dashboard_2012/products_2012_vote_nets.pkl, written by vote_vs_sum.py)."""
    import pickle, rp as _rp
    vote = pickle.load(open(os.path.join(REPO, "outputs", "final_dashboard_2012", "products_2012_vote_nets.pkl"), "rb"))[0]
    cur = _rp.nets()

    def run(nets):
        _rp._nets = nets
        cs = {v: _rp.class_sleeves(v) for v in CL}
        out = {v: {k: _rp.stats(cs[v][k])["ir"] for k in ("Carry", "CarryMom")} for v in CL}
        sty = {k: _rp.ew_intersection([cs[v][k].dropna() for v in CL]) for k in _rp.SLEEVES}
        out["all5"] = _rp.stats(pd.concat(sty, axis=1).mean(axis=1, skipna=False))["ir"]
        return out
    try:
        a, b = run(vote), run(cur)
    finally:
        _rp._nets = cur
    return a, b


def s53():
    F = facts(); ir = F["ir"]
    out = [("h2", "5.3 What Skewness Is")]
    P = out.append
    sk = {v: [ir[(v, "Skewness", w)] for w in ("full", "p1", "p2", "p3")] for v in CL}
    chk(sk["metals"][0] < 0 and all(sk[v][0] > 0 for v in ("energy", "ngl", "precious", "agri")) and max(sk[v][0] for v in CL) < 0.3, "Skewness full-sample sign and size")
    chk(all(not all(sk[v][i] > 0 for i in (1, 2, 3)) for v in CL), "Skewness is positive in all three subperiods in no class")
    chk(all(sk[v][1] < 0 for v in ("metals", "energy", "ngl", "precious")) and sk["agri"][1] > 0 and all(sk[v][3] > 0 for v in ("energy", "ngl", "precious", "agri")) and sk["metals"][3] < 0, "Skewness P1 and P3 signs")
    pool = {w: float(np.mean([legs(VARIANTS[v][0], p)[w]["long_pct"] for v in CL for p in VARIANTS[v][1]])) for w in ("p1", "p2", "p3")}
    cls_long = {(v, w): class_long_pct(v, w) for v in ("energy", "ngl") for w in ("p1", "p2", "p3")}
    chk(pool["p1"] < pool["p3"] and pool["p1"] < pool["p2"] and round(pool["p1"]) == 50 and round(pool["p2"]) == 64 and round(pool["p3"]) == 62, "pooled long share by subperiod")
    chk(round(cls_long[("energy", "p1")]) == 47 and round(cls_long[("energy", "p3")]) == 90 and round(cls_long[("ngl", "p1")]) == 68 and round(cls_long[("ngl", "p3")]) == 93, "Energy and NGL long share")
    wti_crash, wti_flip = skew_episode("energy", "WTI", "2020-03-01", "2020-04-30")
    chk(str(wti_flip) == "2020-03-11", "WTI Skewness turns long 11 March 2020")
    bs = bystyle(); b4 = bystyle4()
    cb = {k: bench_corr(bs[k])["Commodity Index"] for k in bs.columns}
    cb4 = {k: bench_corr(b4[k])["Commodity Index"] for k in ("EW PORT", "Inverse Vol")}
    chk(round(cb["Skewness"], 2) == 0.46 and all(abs(cb[k]) < 0.11 for k in ("Momentum", "Carry", "CarryMom", "Value")), "Skewness correlation with the commodity index")
    cl_ci = {v: bench_corr(CS[v]["Skewness"].dropna())["Commodity Index"] for v in CL}
    chk(round(cl_ci["energy"], 2) == 0.44 and round(cl_ci["ngl"], 2) == 0.43 and abs(cl_ci["metals"]) < 0.05 and cl_ci["agri"] < 0, "class Skewness sleeves and the commodity index")
    chk(cb["EW PORT"] > 0.1 and cb["Inverse Vol"] > 0.1 and all(abs(x) < 0.1 for x in cb4.values()), "book correlation with the commodity index with and without Skewness")
    P(("p", f"The explanations so far concern the four core sleeves. Skewness is the sleeve whose results do not follow the pattern explained in Section 5.1. Its full-sample IR is positive in Energy ({S(sk['energy'][0])}), NGL ({S(sk['ngl'][0])}), Precious Metals ({S(sk['precious'][0])}) and Agriculture ({S(sk['agri'][0])}) and negative in Metals ({S(sk['metals'][0])}), and none of these figures is large. "
            f"In no class is the IR positive in all three subperiods. It is negative in P1 in Metals ({S(sk['metals'][1])}), Energy ({S(sk['energy'][1])}), NGL ({S(sk['ngl'][1])}) and Precious Metals ({S(sk['precious'][1])}), and positive in P3 in Energy ({S(sk['energy'][3])}), NGL ({S(sk['ngl'][3])}), Precious Metals ({S(sk['precious'][3])}) and Agriculture ({S(sk['agri'][3])}). "
            f"Agriculture is the reverse of the others in P1 ({S(sk['agri'][1])}) and Metals is negative in P3 ({S(sk['metals'][3])}). The sign of the sleeve therefore depends on the subperiod more than on the class, which is not the pattern of a premium that is earned wherever a storage or hedging channel operates. "
            f"The question is what the sleeve holds when it earns."))
    P(("p", f"The positions answer it. The signal is long when the trailing-year skewness of a product's returns is negative, and skewness stays negative for a long time after a price collapse, so the sleeve can hold the same sign for years. Averaged over the 23 products, it is long on {pool['p1']:.0f}% of days in P1, {pool['p2']:.0f}% in P2 and {pool['p3']:.0f}% in P3. "
            f"The shift is sharpest in the two energy-related classes, where the share of days long rises from {cls_long[('energy', 'p1')]:.0f}% in P1 to {cls_long[('energy', 'p3')]:.0f}% in P3 in Energy and from {cls_long[('ngl', 'p1')]:.0f}% to {cls_long[('ngl', 'p3')]:.0f}% in NGL. "
            f"The WTI sleeve turned long on {wti_flip.day} {wti_flip.strftime('%B %Y')}, in the middle of the 2020 collapse, and the NGL sleeve was short on 24 February 2020 and long from 11 March (20 March in Ethane), so the long positions were in place for the recovery that followed (Sections 4.1.2 and 4.1.4). "
            f"A sleeve that is long through a recovery earns the recovery, irrespective of the skewness signal that put it there. This is the sense in which the P2 and P3 gains in Energy and NGL are largely one long position, and the Precious Metals gain in 2025 and 2026 is of the same kind (Section 4.1.3)."))
    P(("p", f"The consequence is exposure to the level of commodity prices, and the correlations show it. The by-signal Skewness strategy, equal-weighted across the five classes, has a correlation of {N(cb['Skewness'])} with a passive commodity index (DBC), against {N(cb['Momentum'])} for Momentum, {N(cb['Carry'])} for Carry, {N(cb['CarryMom'])} for Carry-Momentum and {N(cb['Value'])} for Value (Table 10). "
            f"The exposure sits in the energy-related classes, where the class sleeve correlates at {N(cl_ci['energy'])} (Energy) and {N(cl_ci['ngl'])} (NGL) with the index, against {N(cl_ci['metals'])} in Metals and {N(cl_ci['agri'])} in Agriculture. "
            f"Adding the sleeve to the four core sleeves moves the correlation of the Equal Weight cross-commodity portfolio with the index from {N(cb4['EW PORT'])} to {N(cb['EW PORT'])}, and that of the Inverse Vol portfolio from {N(cb4['Inverse Vol'])} to {N(cb['Inverse Vol'])} (Section 4.4). "
            f"We read the positive Skewness IRs in these data as exposure to a recovering commodity market and not as a stable premium. The reading is consistent with the positions and the correlations, but the sample holds one major collapse and one recovery, and we cannot say what the sleeve would earn in a different cycle."))
    P(("p", f"The sleeve also differs in construction from the factors on which it is modelled. Fernandez-Perez, Frijns, Fuertes and Miffre (2018) work with a cross-sectional factor that holds long and short positions in commodities ranked by skewness, so that the long and short legs offset much of the exposure to the market's direction. "
            f"Fernandez-Perez, Fuertes and Miffre (2021) apply a cross-sectional sort to energy futures and find no skewness premium. Our sleeve takes one position per product from the sign of the product's own skewness, with no ranking against other products (Section 3.6), so it can be long in every product at once. "
            f"Our results therefore neither test nor contradict theirs. We do not claim that investors pay for lottery-like payoffs in these markets, and the positive IR of the Energy sleeve ({S(sk['energy'][0])}) does not contradict their finding of no premium, because the sleeves are different objects. "
            f"We keep Skewness as the fifth sleeve of every portfolio because it was part of the design, and its low correlation with the other sleeves (Section 4.4) makes it a diversifier inside the class portfolios. We do not treat it as a premium of the same standing as Momentum, Carry and Carry-Momentum in NGL and Energy."))
    return out


# ----------------------------------------------------------------------------- 5.4
def s54():
    from paper_s4c import across_weights
    F = facts(); ir = F["ir"]
    out = [("h2", "5.4 Implications for Portfolio Construction")]
    P = out.append
    bs = bystyle(); b4 = bystyle4(); bk = combined_book()
    ew5, ivb = stats(bs["EW PORT"]), stats(bs["Inverse Vol"])
    EE, EI, II = stats(bk[("EW", "EW")]), stats(bk[("EW", "IV")]), stats(bk[("IV", "IV")])
    e4 = stats(b4["EW PORT"]); e4p = [stats(b4["EW PORT"], w)["ir"] for w in ("p1", "p2", "p3")]
    ng, en = st("ngl", "EW PORT"), st("energy", "EW PORT")
    ps = {d["name"]: d for d in pair_stats(False)}; enng = ps["Energy-NGL"]
    me, pm, ag = (st(v, "EW PORT") for v in ("metals", "precious", "agri"))
    chk(ew5["ir"] < ng["ir"] and ew5["ir"] < enng["ew"]["ir"] and ew5["ir"] > en["ir"] and ew5["vol"] < min(st(v, "EW PORT")["vol"] for v in CL) and ew5["ret"] < ng["ret"] / 3, "five-class book against NGL, Energy-NGL and Energy")
    chk(max(me["ir"], pm["ir"], ag["ir"]) < 0 and EI["ir"] < EE["ir"] and EI["vol"] < EE["vol"] and EI["ret"] < EE["ret"], "Metals, Precious Metals and Agriculture portfolios negative; Inverse Vol across lowers volatility and return")
    w0 = across_weights(0)
    chk(w0["energy"] < 0.2 and w0["ngl"] < 0.2 and all(w0[v] > 0.2 for v in ("metals", "precious", "agri")), "Inverse Vol across weights")
    _neg = [d for d in ps.values() if d["ew"]["ir"] < 0 and d["iv"]["ir"] < 0]
    chk({d["name"] for d in _neg} == {"Metals-Precious Metals", "Metals-Agriculture", "Precious Metals-Agriculture"} and max(d["corr"] for d in _neg) < 0.13, "three weakest pairs have correlations below 0.13")
    chk(ivb["ir"] > ew5["ir"] and II["ir"] < ew5["ir"] and II["ir"] < st("energy", "Inverse Vol")["ir"], "by-signal Inverse Vol ahead; Inverse Vol at both stages behind")
    chk(ew5["ir"] > e4["ir"] and ew5["vol"] < e4["vol"] and all(x > 0 for x in e4p) and cb_ci(bs) > 0.1 and abs(cb_ci(b4)) < 0.1, "Skewness in the book")
    P(("p", f"The portfolio results of Section 4.3 give the main lesson for portfolio construction. Combining the five classes lowers volatility and costs risk-adjusted return. The Equal Weight cross-commodity portfolio has an IR of {S(ew5['ir'])} at a volatility of {pc(ew5['vol'], 1)} and a return of {pc(ew5['ret'], 1)}, against {S(ng['ir'])} for the NGL portfolio (volatility {pc(ng['vol'], 1)}, return {pc(ng['ret'], 1)}) and {S(enng['ew']['ir'])} for the Energy-NGL pair. "
            f"It does better than Energy alone ({S(en['ir'])}), and its volatility is below that of every single class. The classes added to NGL and Energy are weakly correlated with them (Table 9), which is why the volatility falls. They have no premium of their own, however: the Equal Weight portfolios of Metals, Precious Metals and Agriculture have IRs of {S(me['ir'])}, {S(pm['ir'])} and {S(ag['ir'])}. "
            f"In this sample the classes that lowered risk added no return, and the ratio fell. The result describes a sample in which the premium was found in two classes, and it does not show that a book restricted to them would have been the better choice in advance."))
    P(("p", f"The weighting scheme matters less than the choice of classes. Within a class, Equal Weight and Inverse Vol are close in four of the five classes (Section 4.2). Across classes, the choice matters because Inverse Vol gives each class a weight that falls with its volatility, so it favours the classes without a premium: the average weight is {U(w0['energy'])} on Energy and {U(w0['ngl'])} on NGL, against {U(w0['metals'])} on Metals, {U(w0['agri'])} on Agriculture and {U(w0['precious'])} on Precious Metals. "
            f"With Equal Weight within classes, Inverse Vol across them lowers the volatility of the book from {pc(EE['vol'], 1)} to {pc(EI['vol'], 1)} and its return from {pc(EE['ret'], 1)} to {pc(EI['ret'], 1)}, and the IR falls from {S(EE['ir'])} to {S(EI['ir'])}. "
            f"This agrees with Fernandez-Perez, Fuertes and Miffre (2021), who find that equal-weight integration of styles is hard to beat among several integration methods in energy futures, and it is a reminder that a weighting that targets risk is not the same as one that targets reward. "
            f"The by-signal Inverse Vol portfolio, which weights five strategies of similar volatility, is slightly ahead of Equal Weight ({S(ivb['ir'])} against {S(ew5['ir'])}), and Inverse Vol at both stages is behind ({S(II['ir'])})."))
    P(("p", f"Correlation is not the right criterion for choosing classes. Energy and NGL are the most correlated pair of the ten, with an EW PORT correlation of {U(corr_cross('EW PORT').loc['energy', 'ngl'])}, and the Energy-NGL pair has the best IR of the ten under both weightings ({S(enng['ew']['ir'])} and {S(enng['iv']['ir'])}), while the three pairs that combine only classes without a premium have correlations below 0.13 and are the weakest. "
            f"What the pairs share is the premium, and a low correlation between two series without a premium gives nothing to diversify. We note that this ranking was found in the same sample as the premium, so it describes the sample and is not a rule that we can offer for use in advance. "
            f"A practitioner could choose the classes on an ex ante argument, for example that the premium belongs to harder-to-store energy commodities (Virtual Barrels, 2023, p. 109) or to markets in which hedgers pay speculators, but our design does not test either argument."))
    P(("p", f"The Skewness sleeve changes the book in ways that matter for this choice. Adding it to the four core sleeves raises the IR of the Equal Weight book from {S(e4['ir'])} to {S(ew5['ir'])}, lowers its volatility from {pc(e4['vol'], 1)} to {pc(ew5['vol'], 1)} and its maximum drawdown from {pc(e4['mdd'], 1)} to {pc(ew5['mdd'], 1)}, and it shifts the IR from P1 to P3 (Section 4.3). "
            f"It also adds correlation with a commodity index (Section 5.3). A book without it is already positive in every subperiod (IRs of {S(e4p[0])}, {S(e4p[1])} and {S(e4p[2])}) and has essentially no such exposure, so the choice between the two versions is a choice between a higher IR with commodity beta and a lower one without it. "
            f"We do not recommend one over the other."))
    P(("p", f"Two earlier observations bear on these results. Virtual Barrels (2023, p. 86) notes that in a diversified commodity risk premia book most of the profit comes from energy futures and that the other sectors mainly diversify and reduce the denominator of the risk-adjusted return. "
            f"Our data are consistent with this, since the other classes lower volatility but add no return, but the observation concerns the profit contribution of each sector in cross-sectional factor portfolios, which we do not decompose. "
            f"Bogorad (2025a) reports that low correlations across economically distinct strategies give strong performance under simple aggregation, with an equal-weight IR close to one for five strategies (his Table 2), four of which have a positive full-sample IR on their own. "
            f"We aggregate classes and not strategies, and most of the classes we add have no standalone premium. This is consistent with aggregation helping when each component carries some premium and not when most do not, a reading that the two studies do not test and that we leave as an interpretation."))
    return out


def cb_ci(df):
    return bench_corr(df["EW PORT"])["Commodity Index"]


# ----------------------------------------------------------------------------- 5.5
def s55():
    F = facts(); ir = F["ir"]
    out = [("h2", "5.5 Limitations")]
    P = out.append
    vote, summ = _vote_vs_sum()
    chk(round(vote["all5"], 2) == 0.77 and round(summ["all5"], 2) == 0.87, "five-class Equal Weight IR under the earlier and the adopted rule")
    chk(all(summ[v]["Carry"] > vote[v]["Carry"] for v in CL), "Carry higher in every class under the summed rule")
    chk(summ["energy"]["CarryMom"] > vote["energy"]["CarryMom"] and summ["ngl"]["CarryMom"] > vote["ngl"]["CarryMom"] and abs(summ["metals"]["CarryMom"] - vote["metals"]["CarryMom"]) < 0.01 and summ["precious"]["CarryMom"] < vote["precious"]["CarryMom"] and summ["agri"]["CarryMom"] < vote["agri"]["CarryMom"], "Carry-Momentum higher in Energy and NGL, unchanged in Metals, lower in Precious Metals and Agriculture")
    alt = {}
    for key, suf in (("std", "_zsum_std"), ("pm", "_zsum_pm"), ("zd", "_zdiff"), ("raw", "_rawcarry"), ("main", "")):
        D = _getD(suf)
        alt[key] = {"all5": D["combined"]["all5"]["windows"]["full"][0]["ir"],
                    **{v: {r["name"]: r["ir"] for r in D["tabs"][v]["windows"]["full"]} for v in CL}}
    chk(abs(alt["main"]["all5"] - summ["all5"]) < 0.0006, "dashboard main page agrees with the recomputation")
    chk(round(alt["std"]["all5"], 2) == 0.85 and round(alt["pm"]["all5"], 2) == 0.86 and round(alt["zd"]["all5"] + 1e-9, 2) == 0.77 and round(alt["raw"]["all5"] + 1e-9, 2) == 0.79, "alternative five-class IRs")
    chk(max(alt[k]["all5"] for k in ("std", "pm", "zd", "raw")) < alt["main"]["all5"], "the adopted rule has the highest five-class IR of those compared")
    chk(alt["pm"]["agri"]["CarryMom"] > 0 and alt["pm"]["energy"]["CarryMom"] < alt["main"]["energy"]["CarryMom"] and alt["pm"]["ngl"]["CarryMom"] < alt["main"]["ngl"]["CarryMom"] and all(alt[k]["agri"]["CarryMom"] < 0 for k in ("std", "zd", "main")), "per-month spread alternative: only version with positive Agriculture Carry-Momentum, lowers Energy and NGL")
    bs = bystyle()
    nobs = int(bs["EW PORT"].loc["2012-01-01":"2026-09-23"].dropna().shape[0])
    yrs = (pd.Timestamp("2026-09-23") - pd.Timestamp("2012-01-01")).days / 365.25
    per_year = nobs / yrs
    chk(round(per_year) == 247 and abs(252 / per_year - 1 - 0.02) < 0.002 and abs((252 / per_year) ** 0.5 - 1 - 0.01) < 0.002, "observations per year in the combined portfolios")
    cls_py = [len(CS[v]["Momentum"].loc["2012-01-01":"2026-09-23"].dropna()) / yrs for v in CL]
    chk(min(cls_py) > 251 and max(cls_py) < 253, "observations per year in the class portfolios")
    P(("p", "The interpretations above rest on an in-sample historical backtest of fixed rules, and the evidence is limited in the ways listed here. We have run no significance tests and applied no correction for multiple testing. The concentration of the premium in NGL and Energy was found in the same data, among 23 products, five signals, two weighting schemes and ten pairs of asset classes, so the comparison across classes is a selection and not a pre-specified test. "
            f"The subperiods check the stability of a result and are not out-of-sample evidence. The sample is also short in events. Calendar years 2014, 2015, 2020 and 2021 account for {F['en_share4']:.0f}% of the cumulative log return of the Energy Momentum sleeve, and the Skewness results rest on a single collapse and recovery (Section 5.3). "
            "Section 6 is devoted to significance tests and a data-snooping test, and until it is complete the patterns in Section 4 should be read as descriptions."))
    P(("p", f"Some design choices were made by comparing results on the sample window itself. The combination of the two tenor pairs in Carry and Carry-Momentum (Sections 3.3 and 3.4) adds the pairs' z-scores and the pairs' raw slope changes before taking the sign. An earlier rule took the sign of each pair's signal and held no position when the two disagreed. "
            f"Switching to the summed rule lifts the IR of the five-class Equal Weight book from {S(vote['all5'])} to {S(summ['all5'])}. It raises the Carry IR in every class (Energy from {S(vote['energy']['Carry'])} to {S(summ['energy']['Carry'])}, NGL from {S(vote['ngl']['Carry'])} to {S(summ['ngl']['Carry'])}, Metals from {S(vote['metals']['Carry'])} to {S(summ['metals']['Carry'])}, Precious Metals from {S(vote['precious']['Carry'])} to {S(summ['precious']['Carry'])} and Agriculture from {S(vote['agri']['Carry'])} to {S(summ['agri']['Carry'])}), "
            f"and the Carry-Momentum IR in Energy (from {S(vote['energy']['CarryMom'])} to {S(summ['energy']['CarryMom'])}) and NGL ({S(vote['ngl']['CarryMom'])} to {S(summ['ngl']['CarryMom'])}), while leaving it essentially unchanged in Metals and lowering it in Precious Metals (from {S(vote['precious']['CarryMom'])} to {S(summ['precious']['CarryMom'])}) and Agriculture (from {S(vote['agri']['CarryMom'])} to {S(summ['agri']['CarryMom'])}). "))
    P(("p", f"Four other versions of the combination were compared and not adopted, and the adopted one had the highest five-class IR among them: Carry-Momentum with each pair's change standardised by its own volatility ({S(alt['std']['all5'])}), with a change per month of spread between the two contracts ({S(alt['pm']['all5'])}), and with the change of the Carry z-scores (about {S(alt['zd']['all5'] + 1e-9)}), and Carry as the sign of the summed raw slopes with no z-score (about {S(alt['raw']['all5'] + 1e-9)}). "
            f"The spread-per-month version is the only one with a positive Agriculture Carry-Momentum IR ({S(alt['pm']['agri']['CarryMom'])}), at the price of lower IRs in Energy and NGL. The IR of the adopted rule is therefore an in-sample maximum over a small set of candidates, and its advantage over the earlier rule is not evidence that it would hold in another sample."))
    P(("p", "Other choices were also checked against alternatives on an earlier and longer sample, from January 2011 to June 2026, which contains the sample window: the z-score form of Carry against a composite of two signals for each tenor pair, and the default Momentum of three crossovers against pairs of crossovers. "
            "The NGL tenor pairs (F2-F4 and F2-F14, Table 3) are provisional: the second contract reintroduces the heating-season seasonality that an earlier specification, which started the slope at the fourth contract, was chosen to avoid, and the pairs have not been re-examined for liquidity. "
            "None of these choices was estimated over a wide grid of parameters, but none was made independently of the data."))
    P(("p", f"Several features of the implementation also limit the results. The cost of 5 basis points round trip is charged at half that amount, 2.5 basis points, on a roll day (Section 2.4), and we have not run a sensitivity with the full 5 basis points on rolls or with other cost levels. "
            f"The cross-commodity portfolios combine products on the dates that all of them share, which leaves about {per_year:.0f} observations a year against the 252 used to annualise, so their annualised returns are overstated by about 2% (in relative terms) and their IRs by about 1%. The asset-class portfolios are not affected in practice, with between {min(cls_py):.0f} and {max(cls_py):.0f} observations a year. "))
    P(("p", f"Momentum, Carry and Value are computed from the generic price series as supplied, which jump when the generic contract changes, and not from the ratio-adjusted series that earns the returns (Section 2.3). "
            f"The long Carry tenors of Gold (F7), Platinum and Palladium (F5) lie beyond the range that a study of traded volume found fully liquid, no liquidity study exists for Agriculture, and the deep NGL tenors have not been checked. "
            f"Thirty-three missing prices (Heating Oil F13 and Isobutane F14) were filled from the adjacent tenor (Section 2.2), and the returns exclude financing and collateral income (Section 2.4). "
            f"Finally, the explanations in Section 5 rest on no inventory, positioning or participant data, so they are interpretations and not findings."))
    return out


def blocks():
    out = [("h1", "5. Discussion")]
    out.append(("p", "Section 4 shows where the five signals earn a premium and where they do not. This section asks why the pattern takes this form, what the Skewness sleeve is, and what the pattern implies for building a commodity book. "
                     "We read the evidence through the storage and hedging channels set out in Section 1. Every explanation below is an interpretation consistent with the results and not a test of them, because no inventory, positioning or participant data enter the analysis. "
                     "We begin with the two asset classes in which the premium is found, turn to the three in which it is not, then to Skewness, to the implications for portfolio construction and to the limits of the evidence."))
    out += s51()
    out += s52()
    out += s53()
    out += s54()
    out += s55()
    return out


# ----------------------------------------------------------------------------- 7
def conclusion():
    F = facts(); ir = F["ir"]
    B = []
    bs = bystyle(); ew5 = stats(bs["EW PORT"])
    ps = {d["name"]: d for d in pair_stats(False)}; enng = ps["Energy-NGL"]
    chk(all(ir[(v, k, w)] > 0 for v in ("ngl", "energy") for k in ("Momentum", "Carry", "CarryMom") for w in ("p1", "p2", "p3")), "NGL and Energy core sleeves positive in every subperiod")
    chk(max(ir[(v, "Skewness", "full")] for v in CL) < 0.3, "Skewness small")
    sk_ci = bench_corr(bs["Skewness"])["Commodity Index"]
    chk(round(sk_ci, 2) == 0.46, "Skewness correlation with the commodity index")
    chk(ir[("metals", "Value", "full")] == max(ir[("metals", k, "full")] for k in SLEEVES) and ir[("metals", "Value", "full")] > 0.3, "Metals Value the only edge")
    chk(all(ir[(v, k, "full")] < 0 for v in ("precious", "agri") for k in ("EW PORT", "Inverse Vol")), "Precious Metals and Agriculture portfolios negative")
    chk(ew5["ir"] < ir[("ngl", "EW PORT", "full")] and ew5["ir"] < enng["ew"]["ir"], "book below NGL and Energy-NGL")
    B.append(("h1", "7. Conclusion"))
    B.append(("p", "This paper asks in which commodity asset classes a set of rule-based futures signals earns a premium. We apply five fixed signals, Momentum, Carry, Carry-Momentum, Value and Skewness, to 23 futures products in Metals, Energy, Precious Metals, NGL and Agriculture, over one sample window from 1 January 2012 to 23 September 2026 and under one cost assumption of 5 basis points round trip. "
                   "The positions are combined into sleeves, asset-class portfolios and cross-commodity portfolios. Because the rules, the costs and the dates are the same in every class, differences in the results come from the asset class and not from the method."))
    B.append(("p", f"The premium is concentrated. In NGL and in Energy, Momentum, Carry and Carry-Momentum each earn a positive IR in the full sample and in each of the three subperiods, and the Equal Weight portfolios reach IRs of {S(ir[('ngl', 'EW PORT', 'full')])} in NGL and {S(ir[('energy', 'EW PORT', 'full')])} in Energy. "
                   f"Metals has an edge in Value only (IR {S(ir[('metals', 'Value', 'full')])}), and in Precious Metals and Agriculture no core sleeve earns a clear premium and neither portfolio earns a positive IR. "
                   f"Skewness behaves differently. Its IR is positive in four of the five classes but never above {S(max(ir[(v, 'Skewness', 'full')] for v in CL))}, its sign depends on the subperiod, and it correlates at {N(sk_ci)} with a commodity index, so we read it as exposure to a recovering market and not as a stable premium. "
                   f"These patterns are consistent with the roles of storage and of hedgers in the energy-related classes, which we do not test."))
    B.append(("p", f"The portfolio lesson is that diversification across asset classes lowers volatility at a cost in risk-adjusted return. The Equal Weight cross-commodity portfolio has an IR of {S(ew5['ir'])} at a volatility of {pc(ew5['vol'], 1)}, below NGL alone ({S(ir[('ngl', 'EW PORT', 'full')])}) and below the Energy-NGL pair ({S(enng['ew']['ir'])}), because the classes added have no premium of their own. "
                   f"Correlation was a poor guide to which classes to combine, since Energy and NGL are the most correlated pair and also the best, and the weighting scheme mattered less than the choice of classes."))
    B.append(("p", "These are in-sample results of fixed rules. We have run no significance tests, the concentration in NGL and Energy and the combination of the two tenor pairs were found or chosen on the same sample, and a few episodes carry much of the return, so we describe patterns and claim neither statistical significance nor causes. "
                   "Further work should apply significance and data-snooping tests, extend the evidence to later data as it accumulates, test the hedging pressure and speculative pressure channels directly with CFTC positioning data, and study liquidity and capacity, above all in NGL, where the liquid history is short, and in Agriculture and the deepest tenors, for which we have no liquidity study."))
    return B


def _words(bl):
    return sum(len(b[1].split()) for b in bl if b[0] == "p")


if __name__ == "__main__":
    bl = blocks()
    for b in bl:
        print(b[0], b[1]); print()
    print("WORDS Section 5:", _words(bl))
    for b in conclusion():
        print(b[0], b[1]); print()
