"""Room 27: HL and HL2 frozen. Modes:
  check  - rebuild the development frame with hl_core and reproduce hl.py's validation predictions (must match exactly)
  freeze - refit spec B on every development row (1997-2024) for leads 1 and 2, with the frozen comparators and baselines
Usage: python3 -I hl_frozen.py check|freeze"""
import sys, os, json, pickle, hashlib, numpy as np, pandas as pd, sklearn
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hl_core as H
from mk_frame import read_kp
R = '/tmp/r27raw'
rs = H.prep_rsga(pd.read_csv(f'{R}/rsga_parsed.csv')); dg = H.prep_dgd(pd.read_csv(f'{R}/dgd_dev.csv')); kp = read_kp()
mode = sys.argv[1]; out = {}
KM = '--kmax' in sys.argv
for lead, name in (((1, 'HLK'), (2, 'HLK2')) if KM else ((1, 'HL'), (2, 'HL2'))):
    F = H.build(rs, dg, kp, lead, kmax=KM); yr = F.day.dt.year
    assert F.day.max() < pd.Timestamp('2025-01-01', tz='UTC') and F.day.min() >= pd.Timestamp('1995-06-01', tz='UTC')
    if mode == 'check':
        trn = (yr >= 1997) & (yr <= 2016); val = (yr >= 2017) & (yr <= 2024)
        m = H.mdl().fit(F.loc[trn, H.B].values, F.y[trn].values)
        p = m.predict_proba(F.loc[val, H.B].values)[:, 1]
        P = pd.read_csv(f'out/{name}_result_pred.csv'); P['day'] = pd.to_datetime(P.day, utc=True)
        V = F[val].reset_index(drop=True).assign(p_new=p).merge(P[['day', 'p']], on='day', how='outer', indicator=True)
        out[name] = dict(rows_new=int(val.sum()), rows_old=int(len(P)), both=int((V._merge == 'both').sum()),
                         max_abs_dp=float((V.p_new - V.p).abs().max()))
    else:
        trn = (yr >= 1997) & (yr <= 2024)
        T = F[trn]
        bundle = dict(name=name, lead=lead, kmax=KM, features=H.B, sklearn=sklearn.__version__, numpy=np.__version__, pandas=pd.__version__,
                      model=H.mdl().fit(T[H.B].values, T.y.values),
                      swpc_recal=H.mdl().fit(T[['l_hi']].values, T.y.values),
                      swpc_recal_era=H.mdl().fit(T.loc[T.day.dt.year >= 2012, ['l_hi']].values, T.y[T.day.dt.year >= 2012].values),
                      persistence=H.mdl().fit(T[H.PERS].values, T.y.values),
                      recurrence=H.mdl().fit(T[['Ac_rec']].values, T.y.values),
                      pers_season_rec=H.mdl().fit(T[H.PSR].values, T.y.values),
                      climatology=float(T.y.mean()), fit_rows=int(len(T)), fit_events=int(T.y.sum()),
                      fit_span=[str(T.day.min().date()), str(T.day.max().date())])
        os.makedirs('frozen', exist_ok=True); fn = f'frozen/{name}_frozen.pkl'
        pickle.dump(bundle, open(fn, 'wb'))
        out[name] = dict(file=fn, sha256=hashlib.sha256(open(fn, 'rb').read()).hexdigest(), fit_rows=bundle['fit_rows'],
                         fit_events=bundle['fit_events'], span=bundle['fit_span'],
                         coef=dict(zip(H.B, np.round(bundle['model'][-1].coef_[0], 4).tolist())))
print(json.dumps(out, indent=1)); json.dump(out, open(f'out/hl_frozen_{mode}{"_kmax" if KM else ""}.json', 'w'), indent=1)
