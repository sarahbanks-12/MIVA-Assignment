# Portfolio 2 - Query processing and optimisation

## Workload

The query asks for the 20 most recent incoming transactions for account 42. It filters on `destination_account`, orders by `created_at DESC, transfer_id DESC` and limits the result. The second ordering column breaks ties deterministically. `queries.sql` also supplies a customer-balance aggregation, daily deposit totals, account reconciliation and a reversal audit query. Actual results are in `evidence/all-query-results.txt`. Evidence was regenerated on 12 November 2026. The benchmark result uses 200,000 seed transfers; all-query-results.txt was captured after transaction and replication tests, at 200,333 transfers. The replication deposit adds a newer result for account 42. Q5 now includes the tested reversals.

## Experiment

The dataset held 200,000 transfers when measured. `portfolio-2-query-optimisation/scripts/benchmark.py` drops only the named experimental index, captures a baseline, creates the composite B-tree index and repeats exactly the same query. Existing primary-key and uniqueness indexes remain in place. The PostgreSQL planner is not forced to select any scan type. The script stops if a captured plan does not have the expected shape (a sequential scan and sort before indexing; an index scan on the new index with no sort afterwards), so the analysis below cannot outlive the plans it describes.

Each configuration receives one warm-up and seven measured `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` runs in the same connection. The result rows are compared for equality. `ANALYZE` refreshes statistics. All seven complete plans for each configuration are saved; the readable text plan is an additional run and may have a slightly different time. This distinction explains why the text plan need not equal the median [2].

| Measure | Before index | After index |
|---|---:|---:|
| Median execution time (ms) | 6.988 | 0.009 |
| Minimum / maximum (ms) | 6.963 / 7.156 | 0.009 / 0.012 |
| Root shared-buffer hits, last measured run | 2317 | 23 |
| Root shared-buffer reads, last measured run | 0 | 0 |

## Reading the plans

Without the composite index, PostgreSQL scans the relation to find the account's rows and sorts the matches. The indexed plan uses the destination-account equality condition and reads entries already in the required order, stopping after 20. The index is `(destination_account, created_at DESC, transfer_id DESC)`. Its measured size is 8,134,656 bytes, approximately 7.76 MiB.

The reduction in buffer work supports the timing result. An extra index is not free: it consumes storage and must be maintained on writes. An index on the destination alone could filter rows but would not supply the full requested order. This index does not optimise every query. A source-account history query would require its own workload analysis rather than an assumption that this index covers it.

## Plans for all five queries

`evidence/all-query-plans.txt` holds an `EXPLAIN (ANALYZE, BUFFERS)` plan for every statement in `queries.sql`, with the JSON form beside it. `portfolio-2-query-optimisation/scripts/explain_queries.py` reads the statements from that file, so the plans cannot drift from the submitted SQL. They were captured on 12 November 2026 after the transaction and replication tests, with 200,333 transfers.

| Query | Purpose | Plan nodes, outermost first | Time (ms) | Shared hits |
|---|---|---|---:|---:|
| Q1 | most recent incoming transactions: fixed account and stable tie-break. | Limit > Index Scan | 0.079 | 26 |
| Q2 | account totals per customer, including customers without accounts. | Limit > Sort > Aggregate > Hash Join > Seq Scan > Hash > Seq Scan | 3.700 | 163 |
| Q3 | daily deposit volume (fixed UTC grouping avoids session timezone drift). | Aggregate > Sort > Seq Scan | 74.726 | 2284 |
| Q4 | reconciliation, expected to return zero discrepancies. | Aggregate > Hash Join > Seq Scan > Hash > Seq Scan | 110.745 | 2657 |
| Q5 | audit trail linking a compensating transfer to the original. | Sort > Nested Loop > Index Scan > Memoize > Index Scan | 0.345 | 690 |

Q2, Q3 and Q4 must visit every customer, transfer or ledger row, so they scan whole relations and aggregate. The composite index cannot help them, and a selective index would not change that unless the queries themselves changed. Only Q1 benefits from the experiment above. These single-run figures show the shape of the work and are not benchmarks.

## Limits of the result

These are small, warm-cache, local server execution times, not application response times or production throughput. `EXPLAIN ANALYZE` adds instrumentation and does not include sending rows to a client. The last measured plans show 0 shared-buffer reads before indexing and 0 after indexing. Indexed times are close to measurement granularity, so a large speedup ratio would overstate the precision of this experiment. Before/after order was fixed, only one account distribution was measured, and there was no write-load benchmark. A stronger evaluation would alternate configurations, vary account selectivity, include representative concurrent traffic and measure insert overhead. The synthetic deposits are evenly distributed; a real bank would have more uneven activity.

PostgreSQL: `PostgreSQL 16.13 (Homebrew) on aarch64-apple-darwin25.2.0, compiled by Apple clang version 17.0.0 (clang-1700.6.3.2), 64-bit`. Host: `macOS-27.2.1-arm64-arm-64bit`. Machine-specific values will change on rerun.

[2] PostgreSQL Global Development Group. *Using EXPLAIN*, PostgreSQL 16 documentation. https://www.postgresql.org/docs/16/using-explain.html
