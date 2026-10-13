"""Recomputes the README's table from the day-by-day forecasts in out/lockbox1/ (standard library only).
Brier score: the mean of (p - y)^2 over days; y = 1 on a day when College's highest observed K-index reaches 5 or more."""
import csv, os
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 'lockbox1')
bs = lambda p, y: sum((a - b) ** 2 for a, b in zip(p, y)) / len(y)
print('model  days  storm days  ours    NOAA issued  NOAA recalibrated  College simple rule')
for m in ('HLK', 'HLK2'):
    r = list(csv.DictReader(open(os.path.join(D, f'pred_{m}.csv'))))
    b = {x['day']: x for x in csv.DictReader(open(os.path.join(D, f'baselines_{m}.csv')))}
    y = [float(x['y']) for x in r]
    ours = bs([float(x['p']) for x in r], y)
    issued = bs([float(x['swpc_raw']) for x in r], y)
    recal = bs([float(x['swpc_recal']) for x in r], y)
    simple = bs([float(b[x['day']]['pers_season_rec']) for x in r], y)
    pct = lambda ref: 100 * (ref - ours) / ref
    print(f"{m:5} {len(r):5} {int(sum(y)):11}  {ours:.4f}  {issued:.4f} ({pct(issued):4.1f} %)  {recal:.4f} ({pct(recal):4.1f} %)  {simple:.4f} ({pct(simple):4.1f} %)")
    print(f"      NOAA's issued number averaged {100 * sum(float(x['swpc_raw']) for x in r) / len(r):.1f} %; storm days {100 * sum(y) / len(y):.1f} %")
