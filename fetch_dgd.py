"""Room 27: SWPC's Daily Geomagnetic Data (DGD) from NCEI: Fredericksburg (mid), College (high), estimated planetary
A and 3-hourly K. Development only: 1995-06-01 .. 2024-12-31 (1994 and 1995 Jan-May are lockbox 2: the 1994 file is never
fetched; 1995's rows before June are dropped at parse, never stored; 2025- is lockbox 1, never fetched).
Yearly files to 2017, then quarterly (the yearly file preferred where both exist). Usage: python3 -I fetch_dgd.py OUTDIR"""
import sys, re, os, hashlib, urllib.request
import pandas as pd
B = 'https://www.ngdc.noaa.gov/stp/space-weather/swpc-products/annual_reports/daily_solar_indices_summaries/daily_geomagnetic_data'
UA = {'User-Agent': 'castle-sun-room27'}
get = lambda u: urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=120).read()
out = sys.argv[1]; os.makedirs(out, exist_ok=True)
names = re.findall(r'href="(\d{4}(?:Q\d)?_DGD\.txt)"', get(B + '/').decode())
years = {}
for n in names:
    y = int(n[:4])
    if y < 1995 or y > 2024: continue
    years.setdefault(y, []).append(n)
pick = []
for y, ns in sorted(years.items()):
    pick += [f'{y}_DGD.txt'] if f'{y}_DGD.txt' in ns else sorted(ns)
rows, man = [], []
for n in pick:
    b = get(f'{B}/{n}'); man.append(f'{n} {hashlib.sha256(b).hexdigest()}')
    for L in b.decode(errors='replace').splitlines():
        p = L.split()
        mo = re.match(r'(\d\d) (\w{3}) (\d\d)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s*$', L)   # old layout (1994-96): 'dd Mon yy  A  k-k-k-k-k-k-k-k ...'
        if mo and len(mo[5].split('-')) == 8:
            yy = int(mo[3]); yy += 1900 if yy > 50 else 2000
            MON = {m: i + 1 for i, m in enumerate('Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split())}
            p = [str(yy), str(MON[mo[2]]), mo[1]]
            for a_, k_ in ((mo[4], mo[5]), (mo[6], mo[7]), (mo[8], mo[9])): p += [a_] + k_.split('-')
        mn = re.match(r'(\d{4}) (\d\d) (\d\d)\s', L)
        if mn:   # yearly/quarterly layout; from 2022 the planetary K carries thirds (2.33) and missing runs read '-1-1-1'
            vals = re.findall(r'-?\d+(?:\.\d+)?', L[10:])
            if len(vals) != 27: continue
            p = [mn[1], mn[2], mn[3]] + vals
        if len(p) != 30 or not re.match(r'\d{4}$', p[0]): continue
        day = pd.Timestamp(int(p[0]), int(p[1]), int(p[2]), tz='UTC')
        if day < pd.Timestamp('1995-06-01', tz='UTC') or day >= pd.Timestamp('2025-01-01', tz='UTC'): continue
        v = [float(x) if re.match(r'-?\d+(?:\.\d+)?$', x) else -1.0 for x in p[3:]]
        for i in range(8):
            rows.append((day + pd.Timedelta(hours=3 * i), v[1 + i], v[10 + i], v[19 + i], v[0], v[9], v[18]))
df = pd.DataFrame(rows, columns=['bin', 'k_fred', 'k_coll', 'k_plan', 'A_fred', 'A_coll', 'A_plan'])
df = df.drop_duplicates('bin', keep='last').sort_values('bin')
df.to_csv(f'{out}/dgd_dev.csv', index=False); open(f'{out}/dgd_MANIFEST.txt', 'w').write('\n'.join(man) + '\n')
print(len(pick), 'files;', len(df), 'bins;', df.bin.min(), df.bin.max())
