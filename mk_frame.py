"""Room 27, route MK / HK: the bin frame. One row per daypre day-1 bin (issue 22:00 UTC on d-1, bins of UT day d).
Development only (asserted). Features fixed in STATE before any validation number is read."""
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lockbox import assert_dev
R = '/tmp/r27raw'

def read_kp(path=f'{R}/kp_dev.txt'):
    rows = []
    for L in open(path):
        if L.startswith('#') or not L.strip(): continue
        p = L.split()
        y, m, d = int(p[0]), int(p[1]), int(p[2])
        day = pd.Timestamp(y, m, d, tz='UTC')
        for i in range(8):
            rows.append((day + pd.Timedelta(hours=3 * i), float(p[7 + i])))
    s = pd.DataFrame(rows, columns=['bin', 'kp']).set_index('bin').kp
    return s[s >= 0]

def dipole_tilt(t):
    """Signed dipole tilt (deg): angle between the dipole axis and the plane perpendicular to the Sun-Earth line
    (geometry only; dipole pole fixed at 80.65 N, 72.68 W, IGRF ~2015)."""
    t = pd.DatetimeIndex(t)
    doy = t.dayofyear.values + (t.hour.values + t.minute.values / 60) / 24
    g = 2 * np.pi / 365.25 * (doy - 1)
    dec = np.radians(23.44) * np.sin(2 * np.pi * (doy - 81) / 365.25)
    eot = 229.18 * (0.000075 + 0.001868 * np.cos(g) - 0.032077 * np.sin(g) - 0.014615 * np.cos(2 * g) - 0.040849 * np.sin(2 * g))  # min
    ut = t.hour.values + t.minute.values / 60
    lon_s = np.radians(-15 * (ut - 12 + eot / 60))
    s = np.stack([np.cos(dec) * np.cos(lon_s), np.cos(dec) * np.sin(lon_s), np.sin(dec)])
    pm, lm = np.radians(80.65), np.radians(-72.68)
    m = np.array([np.cos(pm) * np.cos(lm), np.cos(pm) * np.sin(lm), np.sin(pm)])
    return np.degrees(np.arcsin(np.clip((s * m[:, None]).sum(0), -1, 1)))

def build(leads=(1,)):
    bins = pd.read_csv(f'{R}/daypre_bins_dev.csv'); days = pd.read_csv(f'{R}/daypre_days_dev.csv')
    for d in (bins, days):
        for c in ('issue', 'bin', 'day'):
            if c in d: d[c] = pd.to_datetime(d[c], utc=True)
    bins = bins[bins.issue.dt.hour == 22].copy()
    days = days[days.issue.dt.hour == 22].copy()
    kp = read_kp()
    ind = pd.read_csv(f'{R}/dgd_dev.csv'); ind['bin'] = pd.to_datetime(ind.bin, utc=True); ind = ind.set_index('bin')
    out = []
    for iss, g in bins.groupby('issue'):
        g = g.sort_values('bin').reset_index(drop=True)
        if len(g) != 24: continue
        km = g.k_mid.values.astype(float); kh = g.k_high.values.astype(float)
        d0 = iss.normalize() + pd.Timedelta(days=1)
        last_bin = iss.floor('3h') - pd.Timedelta(hours=3)     # 18-21 UT bin ends at 21:00, before the 22:00 issue
        kp_last = kp.get(last_bin, np.nan)
        prev = kp[(kp.index > last_bin - pd.Timedelta(hours=24)) & (kp.index <= last_bin)]
        kp_max24 = prev.max() if len(prev) == 8 else np.nan
        pk = ind.k_plan.get(last_bin, np.nan); fk = ind.k_fred.get(last_bin, np.nan)
        ck_last = ind.k_coll.get(last_bin, np.nan)
        cprev = ind.k_coll[(ind.index > last_bin - pd.Timedelta(hours=24)) & (ind.index <= last_bin)]
        ck_max24 = cprev.max() if len(cprev) == 8 and (cprev >= 0).all() else np.nan
        if ck_last is not None and ck_last < 0: ck_last = np.nan
        dd = days[days.issue == iss].set_index('lead')
        for i in range(24):
            lead = i // 8 + 1
            if lead not in leads: continue
            b = g.bin[i]
            row = dict(issue=iss, bin=b, lead=lead, hrs=(b - iss).total_seconds() / 3600,
                       k_mid=km[i], k_high=kh[i],
                       mid_pm1=km[max(0, i - 1):i + 2].max(), mid_pm2=km[max(0, i - 2):i + 3].max(),
                       mid_mean2=km[max(0, i - 2):i + 3].mean(), mid_daymax=km[(lead - 1) * 8:lead * 8].max(),
                       high_daymax=kh[(lead - 1) * 8:lead * 8].max(),
                       high_pm1=kh[max(0, i - 1):i + 2].max(), high_pm2=kh[max(0, i - 2):i + 3].max(),
                       high_mean2=kh[max(0, i - 2):i + 3].mean(), collK_last=ck_last, collK_max24=ck_max24,
                       kp_last=kp_last, kp_max24=kp_max24, planK_last=pk, fredK_last=fk,
                       rec27=kp.get(b - pd.Timedelta(days=27), np.nan),
                       rec27_max=kp[(kp.index >= b - pd.Timedelta(days=28)) & (kp.index <= b - pd.Timedelta(days=26))].max(),
                       ut=b.hour, doy=b.dayofyear)
            if lead in dd.index:
                r = dd.loc[lead]
                for c in ('A_Fredericksburg', 'A_Planetary', 'Mid/Active', 'Mid/Minor_Storm', 'Mid/Major-Severe_Storm',
                          'High/Active', 'High/Minor_Storm', 'High/Major-Severe_Storm'):
                    row[c] = r.get(c, np.nan)
            out.append(row)
    F = pd.DataFrame(out)
    F['tilt'] = dipole_tilt(F.bin + pd.Timedelta(minutes=90))
    F['abs_tilt'] = F.tilt.abs()
    F['semi'] = np.cos(4 * np.pi * (F.doy - 80) / 365.25)
    F['kp'] = F.bin.map(kp)
    F['k_fred_obs'] = F.bin.map(ind.k_fred); F['k_plan_obs'] = F.bin.map(ind.k_plan); F['k_coll_obs'] = F.bin.map(ind.k_coll)
    F['yG'] = (F.kp >= 4.66).astype(float).where(F.kp.notna())
    F['yP'] = (F.k_plan_obs >= 4.66).astype(float).where(F.k_plan_obs.notna() & (F.k_plan_obs >= 0))
    F['yF'] = (F.k_fred_obs >= 5).astype(float).where(F.k_fred_obs.notna() & (F.k_fred_obs >= 0))
    F['yC'] = (F.k_coll_obs >= 5).astype(float).where(F.k_coll_obs.notna() & (F.k_coll_obs >= 0))
    assert_dev(F.bin)
    return F

if __name__ == '__main__':
    F = build(leads=(1, 2, 3))
    F.to_csv(f'{R}/mk_frame.csv', index=False)
    print(len(F), 'rows', F.bin.min(), F.bin.max())
