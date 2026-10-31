# EUA data review (2026-10-31)

**Data:** ICE Endex EUA futures, Bloomberg generics F1 to F13 (`Gas_Power_Emissions_Futures.xlsx`, sheets EUA_PX / EUA_VOL / EUA_OI), 2008-04-01 to 2026-10-29, 4,801 trading days.
**Result: no data error found, no correction made.** Two data-structure caveats and a list of daily moves that news sources could not confirm are below.

## 1. Tests run and results

| Test | Result |
|---|---|
| Trading calendar | No weekend dates, no duplicates. Missing weekdays are New Year, 1 May, 24-26 and 31 Dec, Good Friday and Easter Monday; the only two others are 2009-12-28 and 2012-01-02, the UK substitute bank holidays. |
| Holiday rows | 11 rows have F1 = NaN (e.g. 2008-12-26, 2018-04-02, 2019-12-26). They are holidays that Bloomberg kept as empty rows. Harmless: the continuous series just carries the previous day. |
| Stale prices | F1 unchanged from the previous day on at most 5.8% of days in any year (2015); longest run of identical F1 is 2 days; 73 days where F1, F2 and F3 are all unchanged (mostly Christmas weeks and thin days). |
| Curve shape | F2/F1 - 1: median +0.46%, 99th percentile +4.4%, 1st percentile 0.0%; never inverted by more than 0.5%; no day on which F2..F5 is more than 1% below the previous tenor. |
| Price levels | Annual mean of F1 follows the published history: 2008 22.7, 2009 13.2, 2010 14.4, 2011 13.1, 2012 7.4, 2013 4.5, 2014 6.0, 2015 7.7, 2016 5.4, 2017 5.8, 2018 15.9, 2019 24.9, 2020 24.8, 2021 53.6, 2022 80.9, 2023 83.9, 2024 65.6, 2025 74.2. |
| Dated anchors (Wikipedia, EU ETS article) | December 2013 contract closed 2012 at **6.67** in the article; our F4 on 2012-12-31 is **6.67** (exact). Copenhagen, 2009-12-21: article -8.7% to 12.40, ours -8.5% (F1) and 12.45 (F2). Early-Feb-2022 high about 97: ours 96.48 (2022-02-08). 24 Feb 2022 onward: from 97 to below 70: ours 94.7 to 57.9 by 7 March. July 2021 about 57: ours July peak 57.81. 2023 high over 100: ours 97.28 close on 2023-02-21 (the article is intraday). 2013 record lows 2.46 to 2.63 (intraday): ours lowest close 2.72 on 2013-04-17. |
| Daily moves above 10% (40 days) | All 40 move every tenor together (F2, F3, F5 within 4 log-points of F1 on each day): none is a one-contract splice artifact. Total volume (all tenors) was at least the 60-day median on 36 of the 40 days and at least twice the median on 22. |
| Spike-and-revert (bad-print signature) | Nine days reverse more than 70% the next day, all inside news-heavy episodes (2013 backloading votes, Ukraine March 2022). No isolated spike that reverses. |
| Robust outliers | Only 9 days with a robust z above 6; the two the 10% screen missed are 2016-01-20 and 2016-01-25 (-7.6%, -7.4%), part of the 15% fall that opened 2016 (Carbon Pulse). |

## 2. Daily moves checked against news

Confirmed by a source (search 2026-10-31):
2009-12-21 (Copenhagen), 2011-12-20 (+21% in ours; reported +18.8%), 2013-02-19 (committee delays vote; -20% intraday, -8.4% close in ours), 2013-04-16/17 (Parliament rejects backloading; ours 4.70 to 3.05 to 2.72), 2013-07-03 (backloading approved; +9%), 2016-04-26 (a +13% one-day rise, biggest in three years, matches ours +12%; I did not open the article), 2017-01-03 (-11.4%; ours -11.3%), 2018-09-13 (more than 4 euros, nearly 18%; ours 22.92 to 18.87), 2020-03-16/18 (virus sell-off), 2022-03-01 (Dec-22 closed 68.85; ours 68.53) and the 2022 crash (-30% to -42% in about a week; ours -38.8%).

Not matched to a news source (all pass the curve-wide test, most on at least median volume): 2012-01-03, 2012-04-02, 2012-11-15, 2013-01-23, 2013-01-31 and 2013-02-01, 2013-02-13, 2013-02-25, 2013-03-20/21, 2013-04-10, 2013-05-10, 2013-10-21, 2014-02-25, 2014-03-27/28, 2014-04-25, 2016-09-28, 2016-12-21, 2017-03-01, 2020-04-06, 2021-12-09, 2021-12-17, 2022-03-08, plus 2009-02-18/19 and 2011-06-23 (before the reporting window or inside the warm-up).
Special note on **2013-01-31 / 2013-02-01** (-10% then +27%): reports give a record low of 2.81 in late January 2013, below every close in our data (lowest Jan-Feb close 3.33 on 01-31). That fits only if 2.81 was an intraday low on 01-31 followed by the 02-01 rebound. The level then held (4.2 to 4.3 for the following days, and the reported 5 to 4.5 drop on 2013-02-19 matches ours), so it is not a one-day bad print, but the two settlement prices themselves cannot be confirmed without the ICE settlement file.

## 3. Caveats

1. **Far tenors repeat prices in flat-curve years.** F2 equals F3 on 91% of days in 2008, 58% in 2009, 22% in 2010, 24% in 2016, 56% in 2017 and 8% in 2018 (F3 equals F4 similarly). Pre-2012 this is warm-up only. In 2017 the F1-F3 slope is exactly zero on 38% of days (3% over 2012-2026), i.e. the EUA Carry sleeve has little information then (near-zero interest rates).
2. **"EUA Active" in the same file is not a front-month check.** It is a far-dated contract (109 against F1 86 on 2022-08-29), so it cannot be used to validate F1.
3. **Sensitivity.** Setting EUA's return to zero on the 24 big-move days that news could not confirm moves EUA's own EW PORT IR from -0.215 to -0.031 and the Power, Emissions and Nat Gas bucket from 0.046 to 0.154. This is a diagnostic, not a correction: those days pass every data test, and removing losing days is not a valid adjustment. It shows that EUA's negative result is concentrated in a few large moves.

## 4. What would close the remaining gap
The ICE Endex EUA daily settlement file (or Bloomberg `MO1 Comdty` PX_SETTLE through a second route) for the unconfirmed dates above. Not available to this session.

## Sources used
Wikipedia, European Union Emissions Trading System (dated price points); Carbon Pulse headlines (2016-04, 2017-01, 2018-09); Bloomberg headlines of 2013-02-19 and 2013-04-16; Climate Change News (2013-01-25); Climate Home (2011-12-21); UK government press release on backloading; Baltic Times (2013-07).
