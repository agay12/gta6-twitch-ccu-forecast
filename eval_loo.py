#!/usr/bin/env python3
"""Leave-one-out evaluation of the forecaster on the kit's comparables.

Treats every comparable launch as a pseudo-case: its hour-1 print is the
known, hours 2..24 of its release day are the answer, the model is built
from the other comparables only, and the pinball loss (2x max(tau*d,(tau-1)*d),
d = ln(y)-ln(q)) is averaged over every scored item. Also scores the house
persistence baseline on the same items for reference.
"""
import json, math, os, sys, glob, importlib

KIT = "/tmp/gta-kit/gta6-twitch-ccu-forecast-01-kit"
LEVELS = (0.05, 0.25, 0.5, 0.75, 0.95)
Z = (-1.645, -0.674, 0.0, 0.674, 1.645)

def load_cases():
    cases = []
    for fn in sorted(glob.glob(os.path.join(KIT, "input", "*.in"))):
        cases.append(json.load(open(fn)))
    return cases

def all_comparables(cases):
    seen, out = {}, []
    for c in cases:
        for comp in c.get("comparables") or []:
            if comp["name"] not in seen:
                seen[comp["name"]] = comp
                out.append(comp)
    return out

def pinball(y, qs):
    items = []
    for tau, q in zip(LEVELS, qs):
        d = math.log(max(y, 1)) - math.log(max(q, 1e-9))
        items.append(2 * max(tau * d, (tau - 1) * d))
    return items

def evaluate(mod_name, **kwargs):
    mod = importlib.import_module(mod_name)
    cases = load_cases()
    comps = all_comparables(cases)
    results = {}
    for case in cases:
        for comp in [c for c in comps if c["name"] not in
                     {x["name"] for x in (case.get("comparables") or [])}]:
            pass  # practice cases' own answers are not in the kit
    # LOO over comparables: leave one out of the full pool
    per_comp, total_items, total_loss = {}, 0, 0.0
    base_items, base_loss = 0, 0.0
    for target in comps:
        others = [c for c in comps if c["name"] != target["name"]]
        pts = mod.release_day_points(target)
        if not pts.get(1) or pts[1] <= 0:
            continue
        case = {
            "known": [{"hour": 1, "viewers": pts[1]}],
            "comparables": others,
            "forecast": [{"hour": h} for h in range(2, 25)],
        }
        try:
            out = mod.forecast_case(case)
        except Exception as e:
            print(f"  {target['name']}: model error {e}")
            continue
        qs = {r["hour"]: r["q"] for r in out["hours"]}
        p1 = pts[1]
        for h in range(2, 25):
            y = pts.get(h)
            if not y or y <= 0:
                continue
            items = pinball(y, qs[h])
            total_items += len(items)
            total_loss += sum(items)
            # persistence baseline
            bq = [p1 * math.exp(z * 0.15 * math.sqrt(h - 1)) for z in Z]
            bitems = pinball(y, bq)
            base_items += len(bitems)
            base_loss += sum(bitems)
        per_comp[target["name"]] = (total_loss, total_items)
    if total_items:
        print(f"{mod_name}{kwargs}: LOO loss={total_loss/total_items:.4f} "
              f"(items={total_items})  baseline={base_loss/base_items:.4f}")
    return total_loss / max(total_items, 1)

if __name__ == "__main__":
    sys.path.insert(0, "/root/work/gta-repo")
    evaluate("main")
