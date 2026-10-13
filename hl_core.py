"""Room 27: HL / HL2 core, extracted from hl.py for the freeze and the lockbox scorer (identical frame logic; verified by
hl_frozen.py check, which must reproduce hl.py's validation predictions exactly).
Q3 (13 Oct 2026, 11:31 UTC, the bridge's question): in kmax mode an observed College K >= 5 decides a storm day, gaps or not; the issue
day's College features use the observed bins (>= 4 of 7). HL/HL2 (A >= 30) mode unchanged."""
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

A = ['l_hi', 'l_act', 'l_mid', 'kc_last', 'kc_max', 'kc_mean', 'kp_last', 'kp_max']
B = A + ['Ac_rec', 'kp_rec', 'semi']
PERS = ['kc_last', 'kc_max', 'kc_mean']
PSR = ['kc_last', 'kc_max', 'kc_mean', 'semi', 'Ac_rec']   # persistence + season + recurrence (added 02:52, before any opening)
lg = lambda p: np.log(np.clip(p, 0.5, 99.5) / (100 - np.clip(p, 0.5, 99.5)))
mdl = lambda: make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=3000))


def prep_rsga(rs):
    rs = rs.copy()
    rs['d1'] = pd.to_datetime(rs.d1, utc=True); rs['issued'] = pd.to_datetime(rs.issued, utc=True, errors='coerce')
    return rs.sort_values('issued').drop_duplicates('d1', keep='last')


def prep_dgd(dg):
    dg = dg.copy(); dg['bin'] = pd.to_datetime(dg.bin, utc=True); dg = dg.set_index('bin')
    for c in ('k_fred', 'k_coll', 'k_plan', 'A_fred', 'A_coll', 'A_plan'): dg[c] = dg[c].where(dg[c] >= 0)
    return dg


def build(rs, dg, kp, lead=1, kmax=False):
    day = dg.groupby(dg.index.normalize()).agg(A_coll=('A_coll', 'first'), A_fred=('A_fred', 'first'), A_plan=('A_plan', 'first'),
                                               kc_max=('k_coll', 'max'), kc_n=('k_coll', 'count'))
    rows = []
    for _, r in rs.iterrows():
        d = r.d1 + pd.Timedelta(days=lead - 1); iss_day = r.d1 - pd.Timedelta(days=1)
        if d not in day.index or iss_day not in day.index: continue
        prev = dg.loc[iss_day:iss_day + pd.Timedelta(hours=18)]
        kpp = kp[(kp.index >= iss_day) & (kp.index <= iss_day + pd.Timedelta(hours=18))]
        if len(prev) != 7 or len(kpp) != 7: continue
        def g(k): v = r.get(k); return np.nan if pd.isna(v) else float(v)
        kcp = prev['k_coll'].dropna()
        if kmax:   # Q3 (13 Oct, 11:31): the issue day's observed College bins, at least 4 of 7
            if len(kcp) < 4: continue
        elif prev['k_coll'].isna().any(): continue
        rows.append(dict(day=d, hi=g(f'hi_min{lead}') + g(f'hi_maj{lead}'), hi_act=g(f'hi_act{lead}'),
                         mid=g(f'mid_min{lead}') + g(f'mid_maj{lead}'),
                         kc_last=kcp.iloc[-1], kc_max=kcp.max(), kc_mean=kcp.mean(),
                         kp_last=kpp.iloc[-1], kp_max=kpp.max(),
                         Ac_rec=day.A_coll.get(d - pd.Timedelta(days=27), np.nan),
                         kp_rec=kp[(kp.index >= d - pd.Timedelta(days=27)) & (kp.index < d - pd.Timedelta(days=26))].max(),
                         semi=np.cos(4 * np.pi * (d.dayofyear - 80) / 365.25),
                         y=(1.0 if day.kc_max[d] >= 5 else (0.0 if day.kc_n[d] == 8 else np.nan)) if kmax else   # Q3: an observed K >= 5 decides the day
                           (float(day.A_coll[d] >= 30) if not pd.isna(day.A_coll[d]) else np.nan)))
    F = pd.DataFrame(rows).dropna(subset=['hi', 'mid', 'hi_act', 'y', 'Ac_rec', 'kp_rec']).reset_index(drop=True)
    F['l_hi'] = lg(F.hi); F['l_act'] = lg(F.hi_act); F['l_mid'] = lg(F.mid)
    F['blk'] = ((F.day - pd.Timestamp('1980-01-01', tz='UTC')).dt.days // 27).astype(int)
    return F
