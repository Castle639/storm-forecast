"""Reruns the 2025-26 test from public data: lock_hl.py's own functions, unchanged, on 2025-01-01 .. 2026-10-11.
Checks the frozen files against frozen/FREEZE.json first, fetches NOAA SWPC's daily reports and daily geomagnetic data
(NCEI's archive) and GFZ's Kp, then writes out/lockbox1/pred_HLK.csv and pred_HLK2.csv (which should equal the SHA-256
in FREEZE.json) and out/lockbox1/baselines_HLK.csv and baselines_HLK2.csv (the frozen simple baselines, day by day).
Usage: python3 -I rerun_lockbox1.py [RAWDIR]   (RAWDIR caches the downloads; default ./raw)"""
import sys, os, json, hashlib, pickle
ROOT = os.path.dirname(os.path.abspath(__file__)); raw = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'raw'))
out = os.path.join(ROOT, 'out', 'lockbox1'); os.chdir(ROOT); sys.path.insert(0, ROOT)
F = json.load(open('frozen/FREEZE.json'))
for fn, h in F['files'].items():
    assert hashlib.sha256(open(fn, 'rb').read()).hexdigest() == h, f'hash mismatch: {fn}'
src = open('lock_hl.py').read(); head = src[:src.index("today = pd.Timestamp.now")]
ns = {'__name__': 'lock_hl', '__file__': os.path.join(ROOT, 'lock_hl.py')}
sys.argv = ['lock_hl.py', 'rerun', out, raw]
exec(compile(head, 'lock_hl.py', 'exec'), ns)
pd, H = ns['pd'], ns['H']
w0, w1 = pd.Timestamp('2025-01-01', tz='UTC'), pd.Timestamp('2026-10-11', tz='UTC')
info, res, preds = ns['run_window'](w0, w1, False)
for n, P in preds.items():
    P[['day', 'y', 'p', 'hi', 'swpc_raw', 'swpc_recal', 'swpc_recal_era']].to_csv(f'{out}/pred_{n}.csv', index=False)
    B = pickle.load(open(f'frozen/{n}_frozen.pkl', 'rb'))
    pd.DataFrame(dict(day=P.day, y=P.y,
                      persistence=B['persistence'].predict_proba(P[H.PERS].values)[:, 1],
                      recurrence=B['recurrence'].predict_proba(P[['Ac_rec']].values)[:, 1],
                      pers_season_rec=B['pers_season_rec'].predict_proba(P[H.PSR].values)[:, 1],
                      climatology=B['climatology'])).to_csv(f'{out}/baselines_{n}.csv', index=False)
for n in preds:
    h = hashlib.sha256(open(f'{out}/pred_{n}.csv', 'rb').read()).hexdigest()
    print(f'pred_{n}.csv', h, 'equal to the sealed hash' if h == F['sealed_predictions'][f'pred_{n}.csv'] else 'DIFFERENT from the sealed hash')
print(json.dumps({n: dict(status=r['status'], brier=r['brier'], c1=r['c1'], c2=r['c2'], c3=r['c3']) for n, r in res.items()}, indent=1))
