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
   that has a count in hour 0 of its own UTC release day contributes log
   ratios `r(h) = ln(v(h) / v(0))` for each release-day hour. Launch days share
   a shape: Europe unlocked at midnight local, a trough through the small
   hours, a huge ramp once North America unlocks, a peak in the US evening,
   then decay.
3. **Smoothed location and spread** — each hour's ratios are pooled with their
   neighbours (h−1, h, h+1) across all comparables; the pooled median is the
   shape `m(h)` and the pooled MAD scale (floored at 0.08 nats) the spread
   `s(h)`.
4. **Calibrated quantiles** — the standardized residuals are pooled over every
   comparable and hour; their empirical quantiles capture the fat right tail
   (a launch can run far hotter than typical). Hour `h`'s quantile at level τ
   is `p1 · exp(m(h) + s(h) · e_τ)`, clamped to (0, 1e9] and non-decreasing.

Everything is computed from the case file at run time — no fitted constants,
no randomness, deterministic byte-for-byte output.

## Validation

Leave-one-out over the 34 usable comparables in the kit's practice cases:
mean pinball loss **≈ 0.58** vs **≈ 0.72** for the house persistence baseline
(the kit starter). All four practice cases produce valid output in well under
a second per case.

## Running

```sh
mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

License: MIT (see LICENSE).
