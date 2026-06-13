#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
aps.py - access-point-side monitor. Every 4s it walks the 4 Xiaomi nodes and
prints one aligned line per node in real time (like ping) + logs to aps.csv.

ONE SOURCE PER NODE: every value for a node comes from THAT node's own login —
nothing is cross-referenced from the controller or from lap.csv. So a node's
whole row is consistent: either we logged in and know it all, or we couldn't and
it's all "--". Self-contained and isolated from lap.py.

Per readable node (login OK):
  - ROLE     : its own topo_graph `show` (1 = controller/master, 0 = satellite/
               slave). A slave is a node with a parent.
  - CLIENTS  : how many devices are on it (its wifi_connect_devices list).
  - CH/PWR   : 2.4/5GHz channel & power, plus the roaming KICK threshold.
  - ME_HERE  : yes if THIS laptop's MAC is in the node's client list, else no.
  - SIGNAL   : my RSSI as that node sees me (only when ME_HERE).
A node we can't log into (wrong password / locked) is all "--" — we don't guess.
A node that doesn't answer ping -> ROLE=off.

Auth is gentle: tokens are reused; a 401 parks a node for a cooldown; a 403
"system locked" backs ALL logins off for 2 min so the lockout can clear.

Run:  python3 /Users/ruslan/Documents/tmp/aps.py     (Ctrl-C to stop)

Style: HEADERS in caps, values in lowercase. Unknown/unavailable value = "--"
(the single marker used across both monitors — never "?" or anything else).
"""
import os, sys, time, re, json, hashlib, random, subprocess
import urllib.request, urllib.parse, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
LOG  = os.path.join(HERE, "aps.csv")
SECS = 4
sys.path.insert(0, HERE)
try:
    from secret import PWD, KEY      # mesh admin creds; secret.py is gitignored, NOT committed
except ImportError:
    sys.exit("aps.py: create secret.py next to the script (copy secret.py.example) with PWD and KEY")
APS  = [("192.168.5.11","main"), ("192.168.5.12","front"),
        ("192.168.5.13","madam"), ("192.168.5.14","tank")]
CONTROLLER = "192.168.5.11"    # the mesh root; its own role is master by definition
SLAVE_COOLDOWN = 60
LOCK_COOLDOWN  = 300   # a "system locked" node needs real quiet time to recover

CFG_KEYS = ["ch_2g","pwr_2g","ch_5g","pwr_5g","bsd","weaken","weakthr","kickthr"]
COLS = ["time","ap","up","rtt","role","clients",
        "ch_2g","pwr_2g","ch_5g","pwr_5g","kick","me_here","signal"]
FMT  = "%-8s %-6s %-5s %-6s %-7s %-8s %-6s %-7s %-6s %-7s %-5s %-8s %-6s"
HEAD = ("TIME","AP","UP","RTT","ROLE","CLIENTS",
        "CH_2G","PWR_2G","CH_5G","PWR_5G","KICK","ME_HERE","SIGNAL")

def sh(c): return subprocess.run(["sh","-c",c], capture_output=True, text=True).stdout

def own_mac():
    m = re.search(r"\bether\s+([0-9a-f:]+)", sh("ifconfig en0")); return m.group(1).lower() if m else "--"

def ping_ap(ip):
    # 3 pings, not 1: a node is "down" only when ALL fail, so a single lost packet
    # on a lossy Wi-Fi uplink doesn't flip a healthy node to down.
    out = sh("/sbin/ping -c3 -i0.2 -W1000 %s 2>/dev/null" % ip)
    rtts = [float(x) for x in re.findall(r"time=([\d.]+)", out)]
    if not rtts: return ("down", "--")
    return ("up", "%.1f" % sorted(rtts)[len(rtts) // 2])

# ---- auth: reuse tokens, back off on 401/403 (PER NODE, never globally) ------
TOKENS = {}; SLAVE = {}; LOCKED = {}; ALGO = {}

def _hash(algo, nonce):
    H = hashlib.sha1 if algo == "sha1" else hashlib.sha256
    return H((nonce + H((PWD + KEY).encode()).hexdigest()).encode()).hexdigest()

def _attempt(ip, algo):
    n = "0_x_%d_%d" % (int(time.time()), random.randint(1, 99999))
    b = urllib.parse.urlencode({"username":"admin","password":_hash(algo, n),"logtype":"2","nonce":n}).encode()
    try:
        r = urllib.request.urlopen(urllib.request.Request("http://%s/cgi-bin/luci/api/xqsystem/login" % ip, b), timeout=3)
        return json.loads(r.read())
    except urllib.error.HTTPError as e:
        try: return json.loads(e.read())
        except Exception: return {"code": e.code}

def login_raw(ip):
    # firmware differs per node: front/main use SHA256, madam/tank use SHA1. Try the
    # node's known algo, else SHA256 then SHA1 on a 401, and cache the one that works.
    algos = [ALGO[ip]] if ip in ALGO else ["sha256", "sha1"]
    d = {}
    for algo in algos:
        d = _attempt(ip, algo)
        if d.get("token"):
            ALGO[ip] = algo
            return d
        if d.get("code") != 401:   # 403 lock / other -> the other algo won't help
            return d
    return d

def get_token(ip, now):
    t = TOKENS.get(ip)
    if t: return t
    if LOCKED.get(ip, 0) > now: return None       # THIS node is locked, others unaffected
    if SLAVE.get(ip, 0) > now: return None
    try:
        d = login_raw(ip)
    except Exception:
        return None
    tok = d.get("token")
    if tok:
        TOKENS[ip] = tok; return tok
    if d.get("code") == 403:                       # "system locked" on THIS node only:
        LOCKED[ip] = now + LOCK_COOLDOWN           # back off this node, leave the rest alone
        TOKENS.pop(ip, None)                       # drop its now-stale token so recovery is clean
    elif d.get("code") == 401:
        SLAVE[ip] = now + SLAVE_COOLDOWN
    return None

def api(ip, tok, ep):
    return json.loads(urllib.request.urlopen("http://%s/cgi-bin/luci/;stok=%s/api/%s" % (ip, tok, ep), timeout=3).read())

def api_auth(ip, ep, now):
    tok = get_token(ip, now)
    if not tok: return None
    try:
        return api(ip, tok, ep)
    except urllib.error.HTTPError as e:
        if e.code == 401:
            TOKENS.pop(ip, None)
            tok = get_token(ip, now)
            if tok:
                try: return api(ip, tok, ep)
                except Exception: pass
        return None
    except Exception:
        return None

def parse_cfg(d):
    c = {k: "--" for k in CFG_KEYS}; seen = False
    for r in d.get("info", []):
        ci = r.get("channelInfo", {})
        if r.get("ifname") == "wl1":
            seen = True
            c["ch_2g"] = str(ci.get("channel","--")); c["pwr_2g"] = r.get("txpwr","--")
            c["bsd"] = str(r.get("bsd","--")); c["weaken"] = str(r.get("weakenable","--"))
            c["weakthr"] = str(r.get("weakthreshold","--")); c["kickthr"] = str(r.get("kickthreshold","--"))
        elif r.get("ifname") == "wl0":
            seen = True
            c["ch_5g"] = str(ci.get("channel","--")); c["pwr_5g"] = r.get("txpwr","--")
    return c if seen else None

def node_role(ip, now):
    """master/slave from the node's OWN topo_graph `show` (1=controller, 0=satellite)."""
    if ip == CONTROLLER: return "master"
    tg = api_auth(ip, "misystem/topo_graph", now)
    if not tg: return "--"
    return "master" if tg.get("show") == 1 else "slave"

def main():
    f = open(LOG, "a")
    if os.path.getsize(LOG) == 0: f.write(",".join(COLS) + "\n")
    hdr = FMT % HEAD
    print(hdr); print("-" * len(hdr)); sys.stdout.flush()
    while True:
        now = time.time(); t = time.strftime("%H:%M:%S"); mac = own_mac()
        for ip, name in APS:
            up, rtt = ping_ap(ip)
            c = {k: "--" for k in CFG_KEYS}
            role = clients = me = sig = "--"
            if up == "down":
                role = "off"
            else:
                # one source: this node's own login. all-or-nothing.
                cfg = api_auth(ip, "xqnetwork/wifi_detail_all", now)
                parsed = parse_cfg(cfg) if cfg else None
                if parsed is not None:
                    c = parsed
                    role = node_role(ip, now)
                    dv = api_auth(ip, "xqnetwork/wifi_connect_devices", now)
                    if dv is not None:
                        lst = dv.get("list", [])
                        clients = str(len(lst))
                        me = "no"
                        for d in lst:
                            if (d.get("mac") or "").lower() == mac:
                                me = "yes"; sig = str(d.get("signal", d.get("rssi", "--"))); break
            vals = (t, name, up, rtt, role, clients,
                    c["ch_2g"], c["pwr_2g"], c["ch_5g"], c["pwr_5g"], c["kickthr"], me, sig)
            f.write(",".join(map(str, vals)) + "\n"); f.flush()
            print(FMT % vals); sys.stdout.flush()
        print(); sys.stdout.flush()
        time.sleep(SECS)

if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt: print("\nstopped")
