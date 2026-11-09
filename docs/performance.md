# Performance and memory checks

Measured on 2026-11-08 on Windows with Python 3.12.16 and Chromium through
Playwright. Numbers are indicative; rerun the commands below on your own hardware.

## Python: GTFS parse/release cycle

A synthetic GTFS archive (55,127 bytes, 1,500 stop times) was parsed, one stop was
extracted and the raw archive was released:

```text
zip bytes:                 55,127
raw archive held:          55,127
raw archive after release:      0
stop_times kept:            1,500
```

Twenty full parse → extract → release cycles, with `gc.collect()` after each one:

```text
tracemalloc baseline:           0 B
tracemalloc current after: 11,846 B
tracemalloc peak:         572,984 B
current growth:            11,846 B
```

The regression test allows a 1.5 MB current growth and a 12 MB peak, so it catches
a real accumulation while tolerating allocator noise.

For a real provider, the official Poznań GTFS archive is about **11 MB**. Releasing
`_raw` after all hub stops have been extracted removes that whole archive from RAM
(plus a separate tram archive where configured). Tomorrow's small fallback lists are
precomputed before the release so the first-departures behaviour is preserved.

## Python: scheduled times for absolute-time realtime feeds

Feeds that send only an absolute `time` (api6-open, Ełk, WKD) need the schedule at
the stop the vehicle is at. Each stop_times entry therefore keeps `trip_times`: one
`array("i")` of `stop_sequence, seconds` pairs for its trip, up to this stop.
Measured on 2026-11-09 on Linux with Python 3.12 (tracemalloc, entries kept after
the extraction):

```text
                              entries   base       with trip_times   per entry
Toruń, busiest stop               633   223 KiB    375 KiB           +247 B
Toruń, 5 busiest stops          2,679   934 KiB    1,603 KiB         +256 B
Wrocław, busiest stop             829   291 KiB    523 KiB           +287 B
Wrocław, 5 busiest stops        4,028   1,404 KiB  2,497 KiB         +278 B
```

One stop_times pass over the Wrocław archive took 0.46 s before and 0.47 s after;
times are parsed only for the rows that are kept.

## Python: timetable cache

`kiedyPrzyjeżdża` timetables are cached for one hour. The cache is pruned on every
fetch and capped:

```text
expired-only cache: 10 entries -> 0
800 mixed entries:           -> 500
```

The 500 newest entries are kept; the oldest 300 are dropped.

## Card: repeated map/card lifecycles

`tests/e2e/performance-memory.spec.ts` opens and closes the vehicle map 20 times and
checks that no dialogs or cards are left behind:

```text
dialogs after: 0
cards after:   0
```

The heap test creates and removes 30 complete card + map lifecycles, then forces a
Chromium GC through CDP (`HeapProfiler.collectGarbage`):

```text
JS heap baseline: 1,227,400 B
JS heap after:    1,437,348 B
delta:              209,948 B (~205 KiB)
```

The test bound is 4 MiB, which is deliberately generous but still catches a per-card
or per-map leak. Heap measurements are noisy, so this test is opt-in with
`RUN_PERF=1` in normal CI runs.

## How to run

```bash
pytest tests/test_performance_memory.py -q
RUN_PERF=1 npx playwright test tests/e2e/performance-memory.spec.ts
```

Map tiles and the upstream APIs are network resources and are not part of these
measurements. Only the integration's own memory/cache behaviour and the card's DOM/JS
lifecycle are covered.
