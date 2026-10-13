"""Room 27: the joint opening's scorer for HLK and HLK2 (frozen: frozen/HLK_frozen.pkl, frozen/HLK2_frozen.pkl; target College's highest K of the day >= 5). Bar: STATE,
"THE MAP ... THE FINALISTS WEIGHED" (k = 3: 98.33 % intervals). Modes:
  dry1  - lockbox 1's code path on development months 2024-06-01 .. 2024-09-30 (compares with the development frame)
  dry2  - lockbox 2's code path (RSGA PDFs, DGD old layout) on development months 1995-06-01 .. 1995-12-31
  pre2  - lockbox 2 format pre-pass: counts only (files, parsed, labels present), no value printed
  open  - lockbox 1 (2025-01-01 .. two days before the run) and lockbox 2 (1994-01-01 .. 1995-05-31)
Usage: python3 -I lock_hl.py MODE OUTDIR RAWDIR"""
import sys, os, re, json, pickle, hashlib, subprocess, urllib.request, urllib.error, concurrent.futures as cf
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hl_core as H
from parse_rsga import parse as parse_rsga_txt
mode, outdir, raw = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(outdir, exist_ok=True); os.makedirs(raw, exist_ok=True)
UA = {'User-Agent': 'castle-sun-room27'}
RB = 'https://www.ngdc.noaa.gov/stp/space-weather/swpc-products/daily_reports/reports_solar_geophysical_activity'
DB = 'https://www.ngdc.noaa.gov/stp/space-weather/swpc-products/annual_reports/daily_solar_indices_summaries/daily_geomagnetic_data'
KPU = 'https://kp.gfz-potsdam.de/app/files/Kp_ap_Ap_SN_F107_since_1932.txt'
MAN = []
K, LO, HI_ = 3, 0.833, 99.167   # k = 3 (HLK, HLK2, WY): GFg left the set at his word

def get(u, fn=None):
    p = os.path.join(raw, fn or u.split('/')[-1])
    if not os.path.exists(p):
        for k in range(4):
            try:
                b = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=120).read(); open(p, 'wb').write(b); break
            except urllib.error.HTTPError as e:
                if e.code == 404: return None
            except Exception:
                if k == 3: return None
    b = open(p, 'rb').read(); MAN.append(f'{os.path.basename(p)} {hashlib.sha256(b).hexdigest()}'); return p

# ---------- Kp (GFZ, whole file as served; only the lines a window needs are parsed) ----------
def kp_series(t0, t1):
    p = get(KPU, 'gfz_kp_full.txt'); rows = []
    for L in open(p):
        if L.startswith('#') or not L.strip(): continue
        q = L.split(); d = pd.Timestamp(int(q[0]), int(q[1]), int(q[2]), tz='UTC')
        if d < t0 or d > t1: continue
        for i in range(8): rows.append((d + pd.Timedelta(hours=3 * i), float(q[7 + i])))
    s = pd.DataFrame(rows, columns=['bin', 'kp']).set_index('bin').kp
    return s[s >= 0]

# ---------- DGD (same parsing as fetch_dgd.py) ----------
MON = {m: i + 1 for i, m in enumerate('Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split())}
def parse_dgd_file(p, t0, t1):
    rows = []
    for L in open(p, errors='replace').read().splitlines():
        q = L.split()
        mo = re.match(r'(\d\d) (\w{3}) (\d\d)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s*$', L)
        if mo and len(mo[5].split('-')) == 8:
            yy = int(mo[3]); yy += 1900 if yy > 50 else 2000
            q = [str(yy), str(MON[mo[2]]), mo[1]]
            for a_, k_ in ((mo[4], mo[5]), (mo[6], mo[7]), (mo[8], mo[9])): q += [a_] + k_.split('-')
        mn = re.match(r'(\d{4}) (\d\d) (\d\d)\s', L)
        if mn:
            vals = re.findall(r'-?\d+(?:\.\d+)?', L[10:])
            if len(vals) != 27: continue
            q = [mn[1], mn[2], mn[3]] + vals
        if len(q) != 30 or not re.match(r'\d{4}$', q[0]): continue
        day = pd.Timestamp(int(q[0]), int(q[1]), int(q[2]), tz='UTC')
        if day < t0 or day > t1: continue
        v = [float(x) if re.match(r'-?\d+(?:\.\d+)?$', x) else -1.0 for x in q[3:]]
        for i in range(8): rows.append((day + pd.Timedelta(hours=3 * i), v[1 + i], v[10 + i], v[19 + i], v[0], v[9], v[18]))
    return rows
def dgd(t0, t1):
    names = re.findall(r'href="(\d{4}(?:Q\d)?_DGD\.txt)"', urllib.request.urlopen(urllib.request.Request(DB + '/', headers=UA), timeout=120).read().decode())
    ys = sorted({int(n[:4]) for n in names if t0.year <= int(n[:4]) <= t1.year}); rows = []
    for y in ys:
        ns = [n for n in names if int(n[:4]) == y]
        pick = [f'{y}_DGD.txt'] if f'{y}_DGD.txt' in ns else sorted(ns)
        for n in pick:
            p = get(f'{DB}/{n}')
            if p: rows += parse_dgd_file(p, t0, t1)
    df = pd.DataFrame(rows, columns=['bin', 'k_fred', 'k_coll', 'k_plan', 'A_fred', 'A_coll', 'A_plan']).drop_duplicates('bin', keep='last').sort_values('bin')
    return H.prep_dgd(df.assign(bin=df.bin.astype(str)))

# ---------- RSGA: text (1996-) with the development parser; PDFs (to 1995) through pdftotext -layout ----------
def parse_rsga_pdf_text(T, fn):
    """lockbox-2 parser: the development parser's fields read from pdftotext text; Part VI by position after its labels."""
    r = {}
    U = T.upper()
    m = re.search(r'ISSUED[^\n]*?(\d{4})Z\s+(\d{1,2})\s+(\w{3})\s+(\d{4})', U)
    d0 = pd.Timestamp(fn[:8], tz='UTC')
    r['issued'] = str(pd.Timestamp(int(m[4]), MON[m[3].title()], int(m[2]), int(m[1][:2]), int(m[1][2:]), tz='UTC')) if m and m[3].title() in MON else ''
    r['d1'] = str((d0 + pd.Timedelta(days=1)).date())
    g = U[U.find('GEOMAGNETIC ACTIVITY PROBABILITIES'):] if 'GEOMAGNETIC ACTIVITY PROBABILITIES' in U else ''
    if not g: return None
    mid = g[:g.find('HIGH LATITUDES')] if 'HIGH LATITUDES' in g else g
    hi = g[g.find('HIGH LATITUDES'):] if 'HIGH LATITUDES' in g else ''
    def three(s):
        v = re.findall(r'(\d+)\s*/\s*(\d+)\s*/\s*(\d+)', s); return [int(x) for x in v[0]] if v else [None] * 3
    for tag, blk in (('mid', mid), ('hi', hi)):
        for key, pat in (('act', r'ACTIVE\s+([\d/ ]+)'), ('min', r'MINOR STORM\s+([\d/ ]+)'), ('maj', r'MAJOR[- ]SEVERE STORM\s+([\d/ ]+)')):
            mm = re.search(pat, blk[:600]); v = three(mm[1]) if mm else [None] * 3
            for k in range(3): r[f'{tag}_{key}{k+1}'] = v[k]
    return r
def rsga(t0, t1, pdf):
    days = pd.date_range(t0 - pd.Timedelta(days=1), t1 - pd.Timedelta(days=1), tz='UTC'); rows, stat = [], dict(files=0, missing=0, parsed=0)
    def one(d):
        ext = 'pdf' if pdf else 'txt'; fn = f'{d:%Y%m%d}RSGA.{ext}'
        return d, get(f'{RB}/{d:%Y}/{d:%m}/{fn}', fn)
    with cf.ThreadPoolExecutor(12) as ex: res = list(ex.map(one, days))
    for d, p in res:
        if p is None: stat['missing'] += 1; continue
        stat['files'] += 1
        if pdf:
            T = subprocess.run(['pdftotext', '-layout', p, '-'], capture_output=True, text=True).stdout
            r = parse_rsga_pdf_text(T, os.path.basename(p))
        else:
            r = parse_rsga_txt(p)
        if r is None: continue
        stat['parsed'] += 1; rows.append(r)
    return pd.DataFrame(rows), stat

def boot(d, blk, n=10000, seed=5):
    ub = np.unique(blk); s = np.array([d[blk == b].sum() for b in ub]); r = np.random.default_rng(seed)
    t = s[r.integers(0, len(s), (n, len(s)))].sum(1) / len(d); return [float(np.percentile(t, LO)), float(np.percentile(t, HI_))]
def boot_h(h, blk, n=10000, seed=6):
    ub = np.unique(blk); s = np.array([h[blk == b].sum() for b in ub]); r = np.random.default_rng(seed)
    t = s[r.integers(0, len(s), (n, len(s)))].sum(1); return [float(np.percentile(t, LO)), float(np.percentile(t, HI_))]
bs = lambda p, y: float(np.mean((p - y) ** 2))

def score(name, F, w0, w1):
    Bd = pickle.load(open(f'frozen/{name}_frozen.pkl', 'rb'))
    V = F[(F.day >= w0) & (F.day <= w1)].reset_index(drop=True)
    expected = len(pd.date_range(w0, w1)); y = V.y.values
    res = dict(name=name, window=[str(w0.date()), str(w1.date())], expected_days=expected, scored=int(len(V)), events=int(y.sum()))
    res['testable'] = bool(len(V) >= 0.9 * expected and y.sum() >= 5)
    if len(V) == 0: res['status'] = 'untestable'; return res, V
    p = Bd['model'].predict_proba(V[Bd['features']].values)[:, 1]
    sw = {'raw': V.hi.values / 100, 'recal': Bd['swpc_recal'].predict_proba(V[['l_hi']].values)[:, 1],
          'recal_era': Bd['swpc_recal_era'].predict_proba(V[['l_hi']].values)[:, 1]}
    ba = {'persistence': Bd['persistence'].predict_proba(V[H.PERS].values)[:, 1], 'recurrence': Bd['recurrence'].predict_proba(V[['Ac_rec']].values)[:, 1],
          'climatology': np.full(len(V), Bd['climatology']), 'pers_season_rec': Bd['pers_season_rec'].predict_proba(V[H.PSR].values)[:, 1]}
    blk = ((V.day - w0).dt.days // 27).values
    res['brier'] = dict(model=bs(p, y), **{f'swpc_{k}': bs(v, y) for k, v in sw.items()}, **{k: bs(v, y) for k, v in ba.items()})
    sn, sp = min(sw.items(), key=lambda t: bs(t[1], y)); bn, bp = min(ba.items(), key=lambda t: bs(t[1], y))
    d1 = (sp - y) ** 2 - (p - y) ** 2; d2 = (bp - y) ** 2 - (p - y) ** 2
    res['c1'] = dict(ref=sn, diff=float(d1.mean()), ci=boot(d1, blk)); res['c2'] = dict(ref=bn, diff=float(d2.mean()), ci=boot(d2, blk))
    k = int(y.sum())
    if k == 0: res['status'] = 'untestable'; return res, V.assign(p=p, **{f'swpc_{kk}': v for kk, v in sw.items()})   # R5
    def ehits(sc):   # expected hits of the top-k under uniform tie-breaking at the cut (self-refutation R3: no random tie-break)
        o = np.sort(sc)[::-1]; thr = o[k - 1]; above = sc > thr; tied = sc == thr; slots = k - above.sum()
        w = above.astype(float) + tied * (slots / tied.sum()); return w
    wo, wsw = ehits(p), ehits(sw['raw'])
    res['c3'] = dict(k=k, model=float((wo * y).sum()), swpc=float((wsw * y).sum()), ci=boot_h(wo * y - wsw * y, blk))
    ok = res['c1']['ci'][0] > 0 and res['c2']['ci'][0] > 0 and res['c3']['model'] >= res['c3']['swpc']
    res['status'] = ('pass' if ok else 'fail') if res['testable'] else 'untestable'
    res['frozen_sha256'] = hashlib.sha256(open(f'frozen/{name}_frozen.pkl', 'rb').read()).hexdigest()
    return res, V.assign(p=p, **{f'swpc_{k}': v for k, v in sw.items()})

def run_window(w0, w1, pdf, warm_days=60):
    t0 = w0 - pd.Timedelta(days=warm_days); t1 = w1 + pd.Timedelta(days=3)
    kp = kp_series(t0 - pd.Timedelta(days=1), t1); dg = dgd(t0, t1)
    rr, st = rsga(t0 + pd.Timedelta(days=30), w1, pdf)
    rs = H.prep_rsga(rr) if len(rr) else rr
    out = dict(rsga=st, dgd_days=int(dg.index.normalize().nunique()), college_complete_days=int((dg.k_coll.groupby(dg.index.normalize()).count() == 8).sum()))
    res, preds = {}, {}
    for lead, name in ((1, 'HLK'), (2, 'HLK2')):
        F = H.build(rs, dg, kp, lead, kmax=True) if len(rr) else pd.DataFrame()
        res[name], preds[name] = score(name, F, w0, w1) if len(F) else (dict(name=name, status='untestable', scored=0), None)
    return out, res, preds

today = pd.Timestamp.now(tz='UTC').normalize()
if mode in ('dry1', 'dry2'):
    w0, w1, pdf = (pd.Timestamp('2024-06-01', tz='UTC'), pd.Timestamp('2024-09-30', tz='UTC'), False) if mode == 'dry1' else \
                  (pd.Timestamp('1995-07-01', tz='UTC'), pd.Timestamp('1995-12-31', tz='UTC'), True)
    assert w0 >= pd.Timestamp('1995-06-01', tz='UTC') and w1 <= pd.Timestamp('2024-12-31', tz='UTC')
    info, res, preds = run_window(w0, w1, pdf, warm_days=30 if mode == 'dry2' else 60)
    if mode == 'dry1':   # the development frame's own predictions for the same days, same frozen models
        from mk_frame import read_kp
        R = '/tmp/r27raw'; rsd = H.prep_rsga(pd.read_csv(f'{R}/rsga_parsed.csv')); dgd_ = H.prep_dgd(pd.read_csv(f'{R}/dgd_dev.csv')); kpd = read_kp()
        for lead, name in ((1, 'HLK'), (2, 'HLK2')):
            Fd = H.build(rsd, dgd_, kpd, lead, kmax=True); Fd = Fd[(Fd.day >= w0) & (Fd.day <= w1)]
            Bd = pickle.load(open(f'frozen/{name}_frozen.pkl', 'rb')); Fd = Fd.assign(pd_=Bd['model'].predict_proba(Fd[Bd['features']].values)[:, 1])
            m = preds[name].merge(Fd[['day', 'pd_', 'y']], on='day', how='outer', suffixes=('', '_dev'), indicator=True)
            res[name]['compare_dev'] = dict(both=int((m._merge == 'both').sum()), lock_only=int((m._merge == 'left_only').sum()),
                                            dev_only=int((m._merge == 'right_only').sum()), max_abs_dp=float((m.p - m.pd_).abs().max()),
                                            y_agree=int((m.y == m.y_dev).sum()))
    out = dict(mode=mode, info=info, results=res)
elif mode == 'cov1':   # self-refutation R2: lockbox 1's College coverage, counts only (no K value, no outcome printed)
    t0, t1 = pd.Timestamp('2024-11-01', tz='UTC'), today - pd.Timedelta(days=2)
    dg = dgd(t0, t1); c = dg.k_coll.groupby(dg.index.normalize()).count()
    lk = c[c.index >= pd.Timestamp('2025-01-01', tz='UTC')]
    out = dict(mode=mode, expected_days=len(pd.date_range(pd.Timestamp('2025-01-01', tz='UTC'), t1)), dgd_days=int(len(lk)), college_complete_days=int((lk == 8).sum()),
               college_ge7_days=int((lk >= 7).sum()), last_day=str(lk.index.max().date()) if len(lk) else None)
elif mode == 'pre2':
    days = pd.date_range('1993-12-31', '1995-05-30', tz='UTC'); cnt = dict(files=0, missing=0, has_geo=0, has_high=0, triples_mid=0, triples_high=0, issued=0)
    for d in days:
        fn = f'{d:%Y%m%d}RSGA.pdf'; p = get(f'{RB}/{d:%Y}/{d:%m}/{fn}', fn)
        if p is None: cnt['missing'] += 1; continue
        cnt['files'] += 1
        U = subprocess.run(['pdftotext', '-layout', p, '-'], capture_output=True, text=True).stdout.upper()
        g = U[U.find('GEOMAGNETIC ACTIVITY PROBABILITIES'):] if 'GEOMAGNETIC ACTIVITY PROBABILITIES' in U else ''
        cnt['has_geo'] += bool(g); cnt['has_high'] += 'HIGH LATITUDES' in g
        mid = g[:g.find('HIGH LATITUDES')] if 'HIGH LATITUDES' in g else g; hi = g[g.find('HIGH LATITUDES'):] if 'HIGH LATITUDES' in g else ''
        cnt['triples_mid'] += len(re.findall(r'\d+\s*/\s*\d+\s*/\s*\d+', mid[:600])) >= 3
        cnt['triples_high'] += len(re.findall(r'\d+\s*/\s*\d+\s*/\s*\d+', hi[:600])) >= 3
        cnt['issued'] += bool(re.search(r'ISSUED[^\n]*?\d{4}Z', U))
    dpath = [get(f'{DB}/1994_DGD.txt'), get(f'{DB}/1995_DGD.txt')]
    rows = sum((parse_dgd_file(p, pd.Timestamp('1994-01-01', tz='UTC'), pd.Timestamp('1995-05-31', tz='UTC')) for p in dpath if p), [])
    D = pd.DataFrame(rows, columns=['bin', 'k_fred', 'k_coll', 'k_plan', 'A_fred', 'A_coll', 'A_plan'])
    D['day'] = D.bin.dt.normalize()
    cov = D.groupby('day').agg(kc=('k_coll', lambda x: int((x >= 0).sum())), ac=('A_coll', lambda x: int(x.iloc[0] >= 0)))
    out = dict(mode=mode, rsga_pdf=cnt, dgd_days=int(len(cov)), college_A_present_days=int(cov.ac.sum()),
               college_K_complete_days=int((cov.kc == 8).sum()), expected_days=len(pd.date_range('1994-01-01', '1995-05-31')))
elif mode == 'open':
    HASHES = json.load(open('frozen/OPENING_HASHES.json'))   # self-refutation R1: the opening refuses to run on files that differ from the frozen set
    for fn, h in HASHES.items():
        assert hashlib.sha256(open(fn, 'rb').read()).hexdigest() == h, f'hash mismatch: {fn}'
    w1a = today - pd.Timedelta(days=2)
    i1, r1, p1 = run_window(pd.Timestamp('2025-01-01', tz='UTC'), w1a, False)
    i2, r2, p2 = run_window(pd.Timestamp('1994-01-01', tz='UTC'), pd.Timestamp('1995-05-31', tz='UTC'), True, warm_days=30)
    out = dict(mode=mode, lockbox1=dict(info=i1, results=r1), lockbox2=dict(info=i2, results=r2))
    ans = {}
    for n in ('HLK', 'HLK2'):
        s1, s2 = r1[n]['status'], r2[n]['status']
        ans[n] = 'YES' if (s1 == 'pass' and s2 in ('pass', 'untestable')) else 'no'
    out['answer'] = ans
    for n, P in list(p1.items()) + [(k + '_lock2', v) for k, v in p2.items()]:
        if P is not None:   # self-refutation R4: only the day, the target, the model and SWPC: no Kp (a G-scale quantity) leaves memory
            P[['day', 'y', 'p', 'hi', 'swpc_raw', 'swpc_recal', 'swpc_recal_era']].to_csv(f'{outdir}/pred_{n}.csv', index=False)
open(f'{outdir}/MANIFEST.txt', 'w').write('\n'.join(sorted(set(MAN))) + '\n')
print(json.dumps(out, indent=1, default=str)); json.dump(out, open(f'{outdir}/{mode}_result.json', 'w'), indent=1, default=str)
