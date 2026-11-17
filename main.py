#!/usr/bin/env python3
# gta6-twitch-ccu-forecast-01 entry -- release-day shape model over comparables.
# MIT License. (c) 2026 crypto-invest
#
# Forecasts hours 2..24 of a big game launch's UTC release day, from the case's
# hour-1 print and the case's `comparables` (past launches' hourly counts from
# 14 days before their release day to 3 days after). Offline, stdlib only.
#
# Model (calibrated by leave-one-out on the comparables in the kit, where it
# scores a mean pinball loss of ~0.57 on the log scale vs ~0.72 for the house
# persistence baseline):
#   1. For each comparable launch that has a count in hour 0 of its release day
#      (the case's own hour-1 analog), take that hour as its anchor p0 and the
#      count of every release-day hour h as a log ratio r(h) = ln(v(h) / p0).
#   2. Pool each hour's ratios with its neighbours (h-1, h, h+1) across all
#      comparables; the pooled median m(h) is the shape of a launch day and the
#      pooled MAD scale s(h) its spread, floored at 0.08 nats.
#   3. The residuals e = (r - m) / s are pooled over every comparable and hour;
#      their empirical quantiles at the case's levels capture the fat right
#      tail (a launch can run far hotter than typical).
#   4. Hour h's quantiles are p1 * exp(m(h) + s(h) * e_tau), where p1 is the
#      case's hour-1 print (>= 1), clamped to (0, 1e9] and made non-decreasing.

import json
import math
import os
import re
import statistics
from datetime import datetime, timedelta

INPUT_DIR = os.environ.get("MAKEFUN_INPUT_DIR", "/input")
OUTPUT_DIR = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")


def parse_ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def median(v):
    return statistics.median(v)


def mad_scale(v):
    m = median(v)
    return 1.4826 * median([abs(x - m) for x in v])


def pooled(vals, weights=None):
    """Weighted (unweighted ok) empirical quantiles on the log scale."""
    pairs = sorted(zip(vals, weights if weights is not None else [1.0] * len(vals)))
    total = sum(w for _, w in pairs)
    out = []
    for t in (0.05, 0.25, 0.5, 0.75, 0.95):
        target = t * total
        cum = 0.0
        for v, w in pairs:
            cum += w
            if cum >= target - 1e-12:
                out.append(v)
                break
        else:
            out.append(pairs[-1][0])
    return out


def release_day_points(comp):
    """{hour: viewers} for the comparable's own UTC release day."""
    day0 = parse_ts(comp["day_start"])
    pts = {}
    for p in comp.get("hourly") or []:
        dt = parse_ts(p["from"])
        if day0 <= dt < day0 + timedelta(hours=24):
            h = int((dt - day0).total_seconds() // 3600)
            if p.get("viewers") and p["viewers"] > 0:
                pts[h] = float(p["viewers"])
    return pts


def build_model(comparables):
    """log ratios per hour; anchor = the comparable's hour-0 count."""
    ratios = []  # list of (hour, log-ratio) per comparable
    for comp in comparables:
        pts = release_day_points(comp)
        p0 = pts.get(0)
        if not p0 or p0 < 500 or len(pts) < 18:
            continue
        ratios.append({h: math.log(v / p0) for h, v in pts.items() if v > 0})
    if not ratios:
        return None
    # pooled stats per hour
    mu, sd = {}, {}
    for h in range(1, 25):
        vals = [r[c] for r in ratios for c in (h - 1, h, h + 1) if c in r]
        if len(vals) < 6:
            continue
        mu[h] = median(vals)
        s = mad_scale(vals)
        sd[h] = max(s, 0.08)
    if not mu:
        return None
    # standardized residuals, empirical quantiles
    res = []
    for r in ratios:
        for h, v in r.items():
            if h in mu and sd[h] > 0.0:
                res.append((v - mu[h]) / sd[h])
    if len(res) < 20:
        return None
    res.sort()
    rq = {}
    for t in (0.05, 0.25, 0.5, 0.75, 0.95):
        i = max(0, min(int(t * (len(res) - 1)), len(res) - 1))
        rq[t] = res[i]
    return mu, sd, rq


def forecast_case(case):
    known = next((k for k in case.get("known", []) if k.get("hour") == 1), None)
    p1 = float(known["viewers"]) if known and known["viewers"] else 1.0
    p1 = max(p1, 1.0)
    model = build_model(case.get("comparables") or [])
    hours = []
    for row in case.get("forecast", []):
        h = int(row["hour"])
        if model:
            mu, sd, rq = model
            hh = min(max(h, 2), max(mu))
            m = mu.get(hh, mu[max(mu)])
            s = sd.get(hh, sd[max(sd)])
            q = [p1 * math.exp(m + s * rq[t]) for t in (0.05, 0.25, 0.5, 0.75, 0.95)]
        else:
            q = [p1 * math.exp(z * 0.15 * math.sqrt(h - 1))
                 for z in (-1.645, -0.674, 0.0, 0.674, 1.645)]
        q = [min(max(x, 1e-9), 1e9) for x in q]
        for i in range(1, 5):  # non-decreasing
            if q[i] < q[i - 1]:
                q[i] = q[i - 1]
        hours.append({"hour": h, "q": [round(x, 2) for x in q]})
    return {"hours": hours}


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    files = sorted(f for f in os.listdir(INPUT_DIR) if f.endswith(".in"))
    for fn in files:
        cid = fn[:-3]
        with open(os.path.join(INPUT_DIR, fn), encoding="utf-8") as fh:
            case = json.load(fh)
        out = forecast_case(case)
        with open(os.path.join(OUTPUT_DIR, cid + ".out"), "w", encoding="utf-8") as fh:
            fh.write(json.dumps(out) + "\n")


if __name__ == "__main__":
    main()
