# reddit_exp5 — Real-World Reddit Validation (Aspect-Level Tunnel Vision)

Self-contained module for the real-data experiments in the TunnelVision paper. It mines
focused Reddit threads for **aspect-level tunnel vision** — the narrowing of attention over
`(aspect, sentiment)` pairs — using genuine **aspect-based sentiment analysis (ABSA)** rather
than topic modeling, and then seeds the Bayesian Multifaceted Engagement Model (MEM) from each
thread's early phase to study formation and mitigation.

All aspect-sentiment annotations are produced by **gpt-5-mini** (ACSA against a frozen
per-thread aspect schema) and **content-hash cached**, so after the first paid pass the whole
pipeline is offline, free, and reproducible.

## The three datasets

Medium-length, focused April-2019 (Pushshift) threads, each verified to narrow at the aspect
level (sliding-window `rho_ASPE < 0`, `rho_conc > 0`). Internal index 0–2 = paper Datasets 4–6.

| DS  | id     | subreddit          | topic                                 | comments | aspects | rho_ASPE | rho_conc |
|-----|--------|--------------------|---------------------------------------|----------|---------|----------|----------|
| DS4 | bbf7wd | r/newzealand       | gun-club / firearms-regulation debate | 173      | 10      | -0.67    | +0.75    |
| DS5 | bix6la | r/PurplePillDebate | the 80-20 rule (dating) debate        | 183      | 9       | -0.65    | +0.53    |
| DS6 | bgknkt | r/bayarea          | Nextdoor / NIMBYism housing debate    | 253      | 11      | -0.42    | +0.37    |

## Layout

```
reddit_config.py            datasets + paths + sys.path shim to the core framework
reddit_absa_extract.py      frozen-schema ACSA extractor (gpt-5-mini, cached)
reddit_utils.py             comment usability + timestamp helpers
analysis_reddit_tv.py       sliding-window ASPE/CASE + concentration metrics, seeding cut
Experiments_reddit_main.py  snapshot loading, seeding, growing-window analysis
Experiments_reddit_seeds.py scenario grid + single seeded MEM run (greedy + random ablations)

scan_absa_collect.py        [1] stream the dump -> candidate thread pool    (free)
scan_absa_prescreen.py      [2] gpt-5-mini ABSA pre-screen -> ranking.csv   (paid)
scan_verify_full.py         [3] full frozen-schema ACSA on top candidates   (paid, cached)
scan_full_replication.py    [4] 10-seed MEM experiments -> tables           (offline)
scan_make_narrowing_fig.py  [5] raw-thread narrowing figures                (offline)
scan_make_exp_figures.py    [5] formation / mitigation / early-late figures (offline)

aspect_schemas/<sid>.json   frozen aspect schema per thread (names, definitions, cues)
data/absa_cache/            cached ACSA labels (per sid)            [derived data, committed]
data/snapshots_absa_scan/   framework snapshots (per thread)        [derived data, committed]
data/scan_verify_exports/   per-comment (aspect, sentiment) CSVs    [derived data, committed]
data/reddit_cut_points_scan.json   per-thread seeding cut points
scan_absa/ranking.csv       300-thread pre-screen ranking (scan output)
scan_absa/selected.json     candidate pool metadata
scan_absa/threads/<sid>.json raw comments for the 3 paper threads
results/                    seeds_scan/ per-(config,seed) curves + scan_table*.csv
figures/                    regenerated PDFs
```

## Setup

The module reaches up one directory for the core framework classes (`Event`, `Comment`,
`SNTUser`, `SNTPlatform`, `analysis_analyzer`, `algorithm_collections`), so run it from inside
the parent project. Python 3.

```
pip install openai scipy pandas numpy matplotlib python-dotenv
```

Paid stages need an OpenAI key in a `.env` at the project root:

```
OPENAI_API_KEY=sk-...
```

## Running

The offline stages reproduce every paper number and figure from the committed caches — no API
key needed:

```
python scan_full_replication.py     # [4] 10-seed experiments -> results/ tables (cache-first)
python scan_make_narrowing_fig.py   # [5] raw-thread narrowing figures
python scan_make_exp_figures.py     # [5] formation / mitigation / early-late figures
```

Rebuilding the data pipeline from scratch (the prescreen and verify stages call the API and
recreate the `scan_absa/cache_extract`, `cache_canon`, and `prescreen` caches):

```
python scan_absa_collect.py         # [1] requires the local Pushshift .zst dumps + zstd
python scan_absa_prescreen.py       # [2] gpt-5-mini pre-screen of the candidate pool
python scan_verify_full.py          # [3] full ACSA verification of the top candidates
```

## Notes

- `scan_verify_full.py`, `data/snapshots_absa_scan/`, and `data/scan_verify_exports/` cover the
  **7** full-method-verified candidate threads; the paper uses the **3** strongest (DS4–DS6).
- Figures are written to this module's `figures/` and, if present, also to `../paper/figures/`.
- Comment text originates from the public Pushshift Reddit April-2019 dump; the aspect schemas
  and aspect-sentiment labels are derived annotations produced for this research.
