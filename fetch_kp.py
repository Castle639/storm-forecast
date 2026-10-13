"""Room 27 (from rooms 25, 26; cut to 1995-06-01..2024): GFZ Kp/ap/Ap/SN/F10.7 since 1932, cut at the lockbox in memory: only lines dated before LOCKBOX_START are written.
The file's sha256 (whole, as served) goes to stdout. Usage: python3 -I fetch_kp.py OUT.txt"""
import sys, os, hashlib, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lockbox import LOCKBOX_START, DEV_START
U = "https://kp.gfz-potsdam.de/app/files/Kp_ap_Ap_SN_F107_since_1932.txt"
b = urllib.request.urlopen(urllib.request.Request(U, headers={"User-Agent": "castle-sun-room27"}), timeout=120).read()
print(U, "sha256(served)", hashlib.sha256(b).hexdigest())
keep = []
for L in b.decode().splitlines():
    if L.startswith('#'): keep.append(L); continue
    y, mo, dd = int(L[:4]), int(L[5:7]), int(L[8:10])
    if (y, mo, dd) >= (DEV_START.year, DEV_START.month, DEV_START.day) and y < LOCKBOX_START.year: keep.append(L)   # both lockboxes cut
open(sys.argv[1], 'w').write("\n".join(keep) + "\n")
print(len(keep), "lines kept (header + days before", LOCKBOX_START.date(), ")")
