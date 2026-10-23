# Search benchmarks

Machine-specific snapshots from the legacy `backend/app/search/engine.py`
benchmark. Re-run on your machine; do not treat these numbers as targets.

## Reproduce

```powershell
$env:PYTHONPATH=(Get-Location).Path
python scripts/benchmark_search.py --output benchmark_optimized.json
python scripts/test_search_concurrency.py
```

`baseline.json` was captured before the query cache, direct FAISS-id map, and
`RLock` fix. `optimized.json` was captured after all three changes. Both use:

- 500 synthetic documents
- 10 natural-language queries
- 10 repetitions per query
- `k=5`
- Intel i5-10210U, 4 cores / 8 threads, 7.8 GB RAM, Windows
- FastEmbed `BAAI/bge-small-en-v1.5` (legacy engine)

Cold timings vary with CPU frequency and system load; compare the warm
(repeated-query) path, which is what the cache targets. The optimized run also
checks that top-5 UIDs match the old linear scan (`result_parity_vs_old_scan`).

## Headline numbers (medians)

| Metric | Baseline | Optimized |
|---|---:|---:|
| Query embedding, cache miss | 12.287 ms | ~12–18 ms (unchanged) |
| Query embedding, cache hit | n/a | 0.002 ms |
| FAISS search | 0.180 ms | 0.138 ms |
| FAISS-id mapping | 0.043 ms (linear scan) | 0.007 ms (direct map) |
| `search_index`, repeated query | 12.630 ms | 0.234 ms |
| Recall@5 | 1.0 | 1.0 |

The active UI path uses `all-MiniLM-L6-v2` and `HybridSearch`; an ad-hoc
500-document run measured ~0.23 ms for the warmed semantic path, ~4 ms for the
SQLite keyword query, and ~4.7 ms end-to-end for a repeated query. The keyword
query is now the active-path bottleneck.
