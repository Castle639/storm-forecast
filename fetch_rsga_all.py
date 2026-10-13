"""Room 25: fetch every NCEI daily RSGA, 1996-01-01 .. DEV_END (the lockbox cut in code).
A 404 is an answer. Usage: python3 -I fetch_rsga_all.py RAWDIR"""
import sys, os, time, urllib.request, urllib.error, concurrent.futures as cf
from datetime import date, timedelta
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lockbox import DEV_END, assert_dev
BASE = "https://www.ngdc.noaa.gov/stp/space-weather/swpc-products/daily_reports/reports_solar_geophysical_activity"
raw = sys.argv[1]; os.makedirs(raw, exist_ok=True)
d0, d1 = date(1996, 1, 1), DEV_END.date()
days = [d0 + timedelta(k) for k in range((d1 - d0).days + 1)]
assert_dev(days)
def one(d):
    fn = f"{d:%Y%m%d}RSGA.txt"; out = os.path.join(raw, fn)
    if os.path.exists(out): return 'have'
    u = f"{BASE}/{d:%Y}/{d:%m}/{fn}"
    for k in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "castle-sun-room27"}), timeout=60) as r:
                open(out, 'wb').write(r.read()); return 'ok'
        except urllib.error.HTTPError as e:
            if e.code == 404: return '404'
            time.sleep(2 ** (k + 1))
        except Exception:
            time.sleep(2 ** (k + 1))
    return 'fail'
with cf.ThreadPoolExecutor(16) as ex:
    res = list(ex.map(one, days))
from collections import Counter
print(len(days), 'days;', Counter(res))
