[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/agay12/gta6-twitch-ccu-forecast/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/agay12/gta6-twitch-ccu-forecast/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

# gta6-twitch-ccu-forecast-01 — release-day shape forecaster

An entry for make.fun's [gta6-twitch-ccu-forecast-01](https://make.fun/bounty/gta6-twitch-ccu-forecast-01):
one hour into GTA VI's release day (2026-11-19 UTC), forecast Twitch's
concurrent viewers in the Grand Theft Auto VI category for each remaining hour
of the day as five quantiles (0.05 / 0.25 / 0.5 / 0.75 / 0.95), scored by mean
pinball loss on the log scale.

## How it works

`main.py` (Python 3.13, standard library only, offline) reads the case file
from `/input` and writes `/output/<id>.out`:

1. **Anchor** — the case's hour-1 print `p1` anchors the whole forecast.
2. **Comparable shape** — every comparable launch in the case's `comparables`
   that has a count in hour 1 of its own UTC release day contributes log
   ratios `r(h) = ln(v(h) / v(1))` for each release-day hour. Anchoring on the
   same hour the case knows keeps the case's print the exact base of the
   shape. Launch days share a shape: midnight unlocks country by country, a
   trough through the small hours, a ramp as North America unlocks, a peak in
   the US evening, then decay.
3. **Smoothed location and spread** — each hour's ratios are pooled with their
   neighbours (h−1, h, h+1) across all comparables; the pooled median is the
   shape `m(h)` and the pooled MAD scale (floored at 0.08 nats) the spread
   `s(h)`.
4. **Calibrated quantiles** — the standardized residuals are pooled over every
   comparable and hour; their empirical quantiles capture the fat right tail
   (a launch can run far hotter than typical). The shape is lifted 10%
   (`SHAPE_GAIN`) and the 5%/95% residuals widened 20% (`TAIL_WIDEN`); both
   values were chosen by the leave-one-out sweep below. Hour `h`'s quantile at
   level τ is `p1 · exp(1.10 · m(h) + s(h) · 1.20 · e_τ)` for the outer
   levels, clamped to (0, 1e9] and made non-decreasing.

Everything is computed from the case file at run time — no fitted constants
beyond the two calibrated scalars, no randomness, deterministic byte-for-byte
output. Without a usable comparable pool the program falls back to the house
persistence shape `p1 · exp(z_τ · 0.15 · √(h−1))`.

## Validation

`eval_loo.py` treats each comparable launch as a pseudo-case: its hour-1 print
is the known, hours 2..24 are the answer, the model is rebuilt from the other
comparables only, and the loss is the contest's own pinball loss.

| model | LOO loss (4070 items) |
| --- | --- |
| house persistence baseline (`p1 · exp(z · 0.15 · √(h−1))`) | 1.0014 |
| hour-0 anchor (first version) | 0.7767 |
| **hour-1 anchor + calibrated gain/tails (this entry)** | **0.7579** |

Run it: `python3 eval_loo.py`. All four practice cases produce valid output in
well under a second per case (`/output` files, 23 rows of 5 quantiles).

A live data check on 2026-11-17 (two days before release), against the same
public endpoint the house reads — `POST https://gql.twitch.tv/gql`,
`game(id: "1867279146") { viewersCount broadcastersCount }` — returned
`viewersCount 8072`, `broadcastersCount 226`: the category exists, is already
live, and the id in the rules is right.

## Running

```sh
mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

License: MIT (see LICENSE).
