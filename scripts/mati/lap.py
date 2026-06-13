#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lap.py - laptop-side monitor. Prints one aligned line every 4s in real time
(like ping) and logs to lap.csv. No sudo. SELF-CONTAINED: it reads ONLY the
laptop (never the routers, never aps.csv) — fully isolated from aps.py.

Columns of note:
  - MEDIUM : wired vs wifi (the interface that actually carries the default
    route, mapped to its hardware port — not hardcoded en0).
  - CH     : the 2.4/5GHz CHANNEL I'm associated on, read locally. We do NOT
    name a node here — channels are dynamic and several nodes can share one, so
    a channel can't identify the node. Which node serves me is answered by the
    other monitor (aps.py, via the controller); this one stays client-only.
  - DEVICE : this Mac's name (scutil), local; falls back to the MAC.
  - quality: ping/loss to the gateway, internet, dns.

Run:  python3 /Users/ruslan/Documents/tmp/lap.py     (Ctrl-C to stop)

Style: HEADERS in caps, values in lowercase. Unknown/unavailable value = "--"
(the single marker used across both monitors — never "?" or anything else).
"""
import os, sys, time, re, subprocess, threading

HERE = os.path.dirname(os.path.abspath(__file__))
LOG  = os.path.join(HERE, "lap.csv")
SECS = 1

MESH_LAN = "192.168.5."     # the MikroTik/mesh LAN
MESH_GW  = "192.168.5.1"    # reachable via phone => repeater, else mobile

COLS = ["time","iface","medium","type","ch","gw","ip","device",
        "link","rssi","txrate","ping_gw","loss","inet","dns"]
FMT  = ("%-8s %-5s %-6s %-8s %-4s %-13s %-15s %-18s "
        "%-11s %-5s %-7s %-7s %-5s %-5s %-4s")
HEAD = ("TIME","IFACE","MEDIUM","TYPE","CH","GW","IP","DEVICE",
        "LINK","RSSI","TXRATE","PING_GW","LOSS","INET","DNS")

def sh(c): return subprocess.run(["sh","-c",c], capture_output=True, text=True).stdout

# ---- interface / medium (local) ---------------------------------------------
def wifi_device():
    out = sh("networksetup -listallhardwareports 2>/dev/null")
    m = re.search(r"Hardware Port:\s*Wi-Fi\s*\nDevice:\s*(\w+)", out)
    return m.group(1) if m else "en0"

WIFI_DEV = wifi_device()
DEVNAME  = (sh("scutil --get ComputerName 2>/dev/null").strip() or "")

def default_iface():
    return sh("route -n get default 2>/dev/null | awk '/interface:/{print $2}'").strip() or "--"

def iface_mac(iface):
    m = re.search(r"\bether\s+([0-9a-f:]+)", sh("ifconfig %s 2>/dev/null" % iface))
    return m.group(1).lower() if m else "--"

def wired_link(iface):
    m = re.search(r"\((\d+base[\w-]+)", sh("ifconfig %s 2>/dev/null" % iface))
    return m.group(1).lower() if m else "wired"

# system_profiler is slow + jittery (~0.8-3s), so it runs in a background thread
# and the main loop just reads this cache. Wi-Fi info refreshes ~every poll;
# the ping/loss cadence is never blocked by it.
_WIFI = {"band": "--", "rssi": "--", "ch": "--", "txrate": "--"}

def _read_wifi():
    # nice: yield CPU so this heavy call doesn't slow the main ping loop's forks
    info = sh("nice -n 19 system_profiler SPAirPortDataType -detailLevel basic 2>/dev/null")
    blk = info.split("Current Network Information:")
    band = ch = rssi = txrate = "--"
    if len(blk) > 1:
        cur = blk[1].split("Other Local")[0]
        m = re.search(r"Channel:\s*([0-9]+)\s*\(([^)]*)\)", cur)
        if m:
            ch = m.group(1)
            band = "5g" if "5GHz" in m.group(2) else ("6g" if "6GHz" in m.group(2) else "2.4g")
        m = re.search(r"Signal / Noise:\s*(-?\d+)", cur)
        if m: rssi = m.group(1)
        m = re.search(r"Transmit Rate:\s*([0-9]+)", cur)   # negotiated link rate, Mbit/s
        if m: txrate = m.group(1)
    return band, rssi, ch, txrate

def wifi_poller():
    # refresh ~every few seconds (system_profiler itself takes ~1-3s); spaced out
    # so it doesn't peg a core and slow the main loop's subprocess calls.
    while True:
        b, r, c, tx = _read_wifi()
        _WIFI["band"], _WIFI["rssi"], _WIFI["ch"], _WIFI["txrate"] = b, r, c, tx
        time.sleep(8)

# ---- probing (local) --------------------------------------------------------
def ping_stats(host, n=3):
    out = sh("/sbin/ping -c%d -W1000 %s 2>/dev/null" % (n, host))
    rtts = [float(x) for x in re.findall(r"time=([\d.]+)", out)]
    loss = 100 - int(100 * len(rtts) / n)
    med = sorted(rtts)[len(rtts) // 2] if rtts else None
    return med, loss

def dns_ok():
    return "ok" if sh("dscacheutil -q host -a name google.com 2>/dev/null | grep ip_address").strip() else "--"

def classify(gw, mesh_reachable):
    # path class only — which network the traffic rides.
    if gw == "--" or not gw:                        return "offline"
    if gw.startswith(MESH_LAN):                     return "mesh"
    if gw.startswith("192.168.4."):                 return "priv"
    if gw.startswith("10.199.237.") or gw.startswith("172.20.10."):
        return "repeater" if mesh_reachable else "mobile"
    return "other"

def main():
    threading.Thread(target=wifi_poller, daemon=True).start()   # slow Wi-Fi read off the critical path
    f = open(LOG, "a")
    if os.path.getsize(LOG) == 0: f.write(",".join(COLS) + "\n")
    hdr = FMT % HEAD
    print(hdr); print("-" * len(hdr)); sys.stdout.flush()
    while True:
        t     = time.strftime("%H:%M:%S")
        iface = default_iface()
        gw    = sh("route -n get default 2>/dev/null | awk '/gateway:/{print $2}'").strip() or "--"
        ip    = sh("ipconfig getifaddr %s 2>/dev/null" % iface).strip() or "--"
        mac   = iface_mac(iface)
        medium = "wifi" if iface == WIFI_DEV else ("wired" if iface != "--" else "--")
        device = DEVNAME or mac

        if medium == "wifi":
            link, rssi, ch, txrate = _WIFI["band"], _WIFI["rssi"], _WIFI["ch"], _WIFI["txrate"]
        elif medium == "wired":
            link, rssi, ch, txrate = wired_link(iface), "--", "--", "--"
        else:
            link, rssi, ch, txrate = "--", "--", "--", "--"

        phone_gw = gw.startswith("10.199.237.") or gw.startswith("172.20.10.")
        mesh_reachable = ping_stats(MESH_GW, 1)[0] is not None if phone_gw else False
        ty = classify(gw, mesh_reachable)

        med, loss = ping_stats(gw) if gw != "--" else (None, 100)
        pg   = "%.1f" % med if med is not None else "--"
        inet = "ok" if ping_stats("1.1.1.1", 1)[0] is not None else "--"
        dns  = dns_ok()

        vals = (t, iface, medium, ty, ch, gw, ip, device,
                link, rssi, txrate, pg, "%d%%" % loss, inet, dns)
        f.write(",".join(map(str, vals)) + "\n"); f.flush()
        print(FMT % vals); sys.stdout.flush()
        time.sleep(SECS)

if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt: print("\nstopped")
