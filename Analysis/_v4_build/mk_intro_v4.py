import sys, os
from docx import Document

src, out = sys.argv[1], sys.argv[2]
if os.path.exists(out):
    sys.exit("exists")
d = Document(src)
P = d.paragraphs


def setp(i, text, startswith):
    assert P[i].text.startswith(startswith), (i, P[i].text[:40])
    P[i].runs[0].text = text
    for r in P[i].runs[1:]:
        r.text = ""


# paragraphs 7 (limits) and 8 (roadmap) are the user's wording and are not touched
keep7, keep8 = P[7].text, P[8].text

setp(1,
"The theory of storage of Kaldor (1939), Working (1949) and Brennan (1958) links the shape of a commodity futures curve to physical market conditions. A downward-sloping curve (backwardation) signals scarce inventories and a high value of immediate supply, and futures prices are then expected to rise toward the spot price. An upward-sloping curve (contango) signals ample inventories, and prices are expected to fall.[1] The hedging pressure hypothesis of Cootner (1960) and Hirshleifer (1988, 1990) offers a second, related channel. Producers and consumers use futures to shed price risk, and speculators who absorb that risk must be paid a premium for doing so. Both theories imply that returns to commodity futures can be predicted from characteristics of the curve and of recent prices, which a long-short strategy can harvest without taking a view on the direction of the commodity market as a whole (Gorton and Rouwenhorst, 2006; Erb and Harvey, 2006; Miffre and Rallis, 2007; Gorton, Hayashi and Rouwenhorst, 2013; Asness, Moskowitz and Pedersen, 2013; Koijen, Moskowitz, Pedersen and Vrugt, 2018). A third strand concerns the shape of the return distribution. Investors who prefer lottery-like payoffs overpay for commodities whose returns are positively skewed and must be compensated for holding those whose returns are negatively skewed, so skewness can also predict returns (Fernandez-Perez, Frijns, Fuertes and Miffre, 2018).",
"The theory of storage")

setp(2,
"Most of this evidence comes from a single sector or from a broad index of commodities. In their study of energy futures, Fernandez-Perez, Fuertes and Miffre (2021) find sizeable premia from term structure, hedging pressure and momentum, find none from skewness, and show that a simple equal-weight combination of signals is hard to beat. It is less clear whether such premia are a general feature of commodity futures or are specific to the sectors where the economics of storage and hedging are strongest. This paper tests that directly. We apply a common set of rule-based signals to futures products in five asset classes (Metals, Energy, Precious Metals, natural gas liquids (NGL) and Agriculture), over one sample period and with the same transaction cost assumptions, and ask where the premium is actually found.",
"Most of this evidence")

setp(3,
"The signals are Momentum, Carry, Carry-Momentum and Value, which capture trend, the slope of the futures curve, changes in that slope, and the deviation of price from its long-run level, together with Skewness, which captures whether a product's recent returns have been crash-prone or spike-prone. We treat all five as risk premia. Each signal is implemented as a simple long, short or flat position in every product and is traded net of transaction costs. We evaluate each signal within each asset class, combine the five signals into an asset-class portfolio, and then combine the asset classes into a cross-commodity portfolio. We also examine whether the results persist across subperiods. The construction of the signals and portfolios is set out in Section 2.",
"The signals are")

setp(4,
"The results are concentrated. For the four core signals, the premium is found in NGL and in Energy and essentially nowhere else. Both earn positive risk-adjusted returns from Momentum, Carry and Carry-Momentum in every subperiod, and NGL is the strongest asset class by a wide margin. In Precious Metals and Agriculture the core signals earn no positive risk-adjusted return, and in Metals only Value shows a clear edge. "
"Skewness behaves differently. It earns a positive return in Energy, Precious Metals and Agriculture, little in NGL and none in Metals, so its pattern across asset classes is not the pattern of the core signals, and it is the only signal with a positive return in Precious Metals and Agriculture. "
"Its returns are also more episodic. They come mainly from the years after large price collapses and reversals, and in Energy they reflect largely a long position held after the 2020 collapse, which makes the signal look more like exposure to a recovering commodity market than a stable premium.",
"The results are concentrated")

setp(5,
"This concentration has a direct consequence for portfolio construction. Diversifying across all five asset classes lowers volatility substantially, and the resulting portfolio is negatively correlated with equities and with a traditional 60/40 portfolio. Skewness raises the portfolio's risk-adjusted return and lowers its volatility further, but it also adds exposure to commodity prices, so the portfolio is no longer negatively correlated with a passive commodity index. "
"Diversification still does not beat concentration on risk-adjusted return. The cross-commodity portfolio performs worse than NGL alone and worse than a portfolio of only Energy and NGL, because the lower volatility is paid for with exposure to asset classes where the core signals earn nothing. Correlation and performance turn out to be separate questions: Energy and NGL are the most correlated pair of asset classes and also the best-performing pair.",
"This concentration")

setp(6,
"The paper contributes in three ways. First, it provides a like-for-like comparison of the same trend, carry, value and skewness signals across five commodity asset classes, using one set of rules, costs and sample dates, so that differences in results reflect the asset class and not the method. The usual single-sector or index-level studies cannot separate the two. "
"Second, it shows that the risk premium is not a property of commodities in general. It appears where physical constraints are strongest and shape the futures curve in a persistent way, such as storage and pipeline capacity in NGL and Energy, and it is weak or absent in Metals, Precious Metals and Agriculture, whose prices are driven more by real yields (Precious Metals), inventory and financing conditions (Metals), and weather and war-related price spikes (Agriculture).[2] "
"Skewness fits the same reading: its gains do not come from the shape of the curve but from the aftermath of price collapses and spikes, and they appear in the asset classes where the curve-based signals fail. "
"Third, it gives a practical portfolio lesson: adding asset classes to a risk premia book to reduce volatility has a cost in risk-adjusted return when most of the added sleeves have no edge, and adding Skewness lowers risk further but at the price of commodity exposure. A smaller portfolio concentrated in NGL and Energy performs better.",
"The paper contributes")

assert P[7].text == keep7 and P[8].text == keep8

# note [2]
i2 = next(i for i, p in enumerate(P) if p.text.startswith("[2]"))
P[i2].runs[0].text = ("[2] Real yields for gold, LME inventory and financing conditions for aluminium and zinc, and weather and war-related spikes in grains and coffee are the explanations documented in Risk Premia Analysis v4_2012. "
                      "They are interpretations consistent with the results, not tests.")
for r in P[i2].runs[1:]:
    r.text = ""

notes = [
"This version has no result numbers. Qualitative claims rest on Risk Premia Analysis v4_2012 (five sleeves, numbers audited against Dimil's dataset) and on Skewness_Research.html. Full-sample IRs behind paragraph 4: Skewness Energy +0.17 (+0.37 ex-NatGas), Precious Metals +0.10, Agriculture +0.25, NGL +0.06, Metals -0.08.",
"What changed from the previous version: paragraph 1 adds the skewness literature (Fernandez-Perez, Frijns, Fuertes and Miffre, 2018, Journal of Banking and Finance 86, 143-158, checked); paragraph 2 notes that the 2021 energy paper finds no skewness premium; paragraph 3 describes Skewness; paragraph 4 describes its pattern and why it is episodic; paragraph 5 drops the claim that the portfolio is negatively correlated with a commodity index (with Skewness it is +0.19 for Equal Weight and +0.14 for Inverse Vol); paragraph 6 lists the macro drivers by asset class and adds the Skewness point.",
"Paragraphs 7 (limits) and 8 (roadmap) are your wording and are unchanged. The roadmap does not yet say where Skewness is covered.",
"This draft assumes Skewness is in the headline portfolios (the v4_2012 basis). If you decide to keep it as a standalone premium, paragraphs 3, 5 and 6 change.",
"'Essentially nowhere else' holds for the four core signals only. Metals Value is the one exception inside them and is named in paragraph 4 without a number. Keep or soften.",
"'Like-for-like' needs a caveat in Methodology: tenor pairs differ by asset class and NGL uses a shifted front contract. The reason for each design choice (NGL second contract, V2 Carry, two tenor pairs, six Agriculture products, roll rule, Value warm-up) goes in Methodology, one line each. The absence of significance tests, and the fact that the NGL and Energy concentration was identified in the same sample, still need a place (Methodology limitations or Conclusion).",
"Research_Methodology_v4 now carries a 2012 variant paragraph and Section 5.8 (Skewness). The Methodology of the new paper must use the 2012 window, P1 to P3, and describe Skewness as the time-series version (one position per product), not the cross-sectional sort of the 2021 paper.",
"Reference list is not built yet. Cited so far: Kaldor (1939); Working (1949); Brennan (1958); Cootner (1960); Hirshleifer (1988, 1990); Gorton and Rouwenhorst (2006); Erb and Harvey (2006); Miffre and Rallis (2007); Gorton, Hayashi and Rouwenhorst (2013); Asness, Moskowitz and Pedersen (2013); Koijen, Moskowitz, Pedersen and Vrugt (2018); Fernandez-Perez, Frijns, Fuertes and Miffre (2018); Fernandez-Perez, Fuertes and Miffre (2021).",
]
bul = [i for i, p in enumerate(P) if p.style.name == "List Bullet"]
for k, i in enumerate(bul):
    if k < len(notes):
        P[i].runs[0].text = notes[k]
        for r in P[i].runs[1:]:
            r.text = ""
    else:
        P[i]._element.getparent().remove(P[i]._element)
d.save(out)
print("saved", out, "| bullets", len(bul), "->", len(notes))
