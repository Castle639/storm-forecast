# Storm forecast

A daily probability of a geomagnetic storm day over Alaska, from Domino Observatory: the chance that College, near Fairbanks, records a K-index of 5 or more on the next UT day (HLK) and on the day after (HLK2). That is the event NOAA's Space Weather Prediction Center verifies its own high-latitude forecast on: "High-latitude forecasts are verified against College, AK observations", with a day's category set by "the highest observed K-index for the day" (SWPC, Geomagnetic Probability Forecast Verification).

Each model is a logistic regression on eleven numbers known when SWPC issues its daily report (RSGA): SWPC's three geomagnetic probabilities for the target day (high-latitude minor plus major-severe storm, high-latitude active, mid-latitude minor plus major-severe storm); College's K over the issue day (its last, highest and mean 3-hour value); the planetary Kp over the issue day (last and highest); College's daily A and the highest Kp 27 days before the target day; and a semiannual season term.

## On years the models never saw

Fitted on 1997-01-13 – 2024-12-31 and frozen, then scored once on 2025-01-01 – 2026-10-11. Brier score, lower is better. NOAA issued: SWPC's high-latitude minor plus major-severe probability for the same day, from its RSGA. NOAA recalibrated: that number refitted on 1997–2024 College days, frozen with the models. College simple rule: College's own persistence, season and 27-day recurrence, refitted and frozen the same way.

| Model | Days | Storm days | Ours | NOAA issued | NOAA recalibrated | College simple rule |
|---|---|---|---|---|---|---|
| HLK, day 1 | 632 | 342 | 0.1964 | 0.2352 | 0.2232 | 0.2077 |
| HLK2, day 2 | 631 | 343 | 0.2175 | 0.2392 | 0.2313 | 0.2354 |

Ours is 16.5 % below NOAA's issued number on day 1 and 9.1 % on day 2; 12.0 % and 5.9 % below it recalibrated; 5.4 % and 7.6 % below College's simple rule. The pass lines were written and committed before the test: better than NOAA's best calibration, better than the strongest simple baseline, each paired interval above zero (98.33 %, 27-day blocks bootstrapped, three candidates opened together), and at least as many storm days caught at NOAA's count. Both models passed. `out/lockbox1/result.json` holds every clause and interval.

NOAA's issued day-1 number averaged 66 % over these days; storms came on 54 % of them.

`python3 score.py` recomputes the table from `out/lockbox1/`.

## Its limits
- These are everyday high-latitude storms: K 5 or more at College came on 54 % of days in 2025–26.
- College's simple rule alone also beats NOAA's issued day-1 number: +0.027 [+0.011, +0.045] in Brier (95 %, 27-day blocks). On day 2 the two are level. This was checked after the test, not one of its pass lines (`out/lockbox1/check_baseline_vs_noaa.json`).
- Storm days caught at NOAA's count: 243 against 231 expected on day 1, an interval that holds zero. More storm days caught is not shown.
- A day with gaps in College's record and no observed K of 5 or more is dropped. Gaps are more common in the biggest storms.
- A second test period, 1994–95, could not be scored: College's record covers 80 of its 516 days.
- A third candidate opened beside these, a planet-wide G1 forecast for the next 24 hours, did not pass.
- There is no daily job yet; the models have run on 2025–26 only.

## Files
- `frozen/`: the two models (scikit-learn pipelines, pickled, with their frozen baselines) and the SHA-256 of every frozen file in `FREEZE.json`. A pickle runs code when loaded: check its hash first.
- `out/lockbox1/`: every day's forecast, ours beside SWPC's issued and recalibrated numbers and the outcome (`pred_*.csv`, whose SHA-256 were sealed by the test before anyone read them); the frozen baselines day by day (`baselines_*.csv`); the test's full record (`result.json`).
- `lock_hl.py`: the scorer that ran the test. `hl_core.py`: the features. `parse_rsga.py`, `lockbox.py`: the report parser and the date guard.
- `hl_frozen.py`, `mk_frame.py`, `fetch_rsga_all.py`, `fetch_dgd.py`, `fetch_kp.py`: the fit on 1997–2024 and its data.
- `rerun_lockbox1.py`: refetches the public data and rebuilds `out/lockbox1/`.

## Run it
    pip install -r requirements.txt
    python3 -I rerun_lockbox1.py    # refetch, rescore, check the sealed hashes
    python3 score.py

Data: SWPC's daily reports and daily geomagnetic data, as archived at NCEI; GFZ Potsdam's Kp.

## Licence
BSD 3-Clause.
