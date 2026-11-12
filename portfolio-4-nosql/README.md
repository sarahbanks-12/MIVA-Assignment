# Portfolio 4 - NoSQL and advanced data models

## Choosing a second store for the same bank

Cedar Bank needs fast-changing notification preferences and short-lived transfer-attempt counters. These values have different requirements from an account balance. Redis is used here as a real key-value database with hashes and sorted sets, not as a simulated Python dictionary. PostgreSQL remains responsible for money movement.

| Key | Type | Example fields/value | Lifetime |
|---|---|---|---|
| cedar:portfolio:customer:42:preferences | Hash | customer_id=42, channel=push, language=en | Persistent in the demo |
| cedar:portfolio:customer:42:attempts | String counter | 20 | 60 seconds from first attempt |
| cedar:portfolio:risk-review | Sorted set | transfer-demo-2 with score 95 | Persistent synthetic queue |

The customer identifier refers conceptually to PostgreSQL's customer 42; Redis does not enforce that foreign key. The sample transfer names and scores are invented review items, not calculated fraud predictions. Preferences are demonstrated separately and do not drive a deployed notification service.

## Implementation and evidence

Run `../portfolio-4-nosql/scripts/test_nosql.py` against the dedicated local Redis instance. It creates, reads, updates and deletes hash fields, ranks three review items, runs 20 concurrent counter increments and observes a one-second key expire. The evidence JSON includes the server version, actual values, TTL and persistence settings. A separate five-second counter is incremented, allowed to age, and incremented again; its measured millisecond TTL must not increase. The expiry test uses the Lua counter itself, not an unrelated SET command.

The counter is implemented by `velocity.lua`. Putting INCR and the first EXPIRE in one server-side script [8] avoids the gap that could leave a counter without an expiry if the client crashed between two separate commands. Only the first attempt starts the window; later attempts do not reset it. Twenty concurrent requests must return exactly the integers 1 through 20. A fixed window can permit bursts around its boundary, so this is a velocity signal rather than a complete rate-limiting or fraud strategy.

## Suitability and trade-offs

A hash lets the application add an optional preference without altering a relational table [4]. TTL removes temporary state, while a sorted set supports a small ordered review list. These are good fits for low-latency auxiliary work. They are poor reasons to move authoritative balances out of PostgreSQL: Redis does not enforce our relational keys or the balanced-ledger rule.

`redis.conf` binds only to loopback and enables append-only persistence with `appendfsync everysec`. Persistence is configured, but a restart/crash recovery test was not performed. AOF everysec is not a promise that the latest acknowledged update survives a crash [5]. Loss of a short-lived counter could weaken a risk control; a real service would need a documented failure policy instead of quietly accepting all requests.

This demonstration makes no atomic cross-database writes. If notifications were added to a transfer service, the transfer and an outbox row should commit together in PostgreSQL. A worker could then publish to Redis and deduplicate delivery by transfer ID. That integration is a proposed extension, not completed evidence.

Only keys under `cedar:portfolio:*` are removed on rerun. The script never uses FLUSHDB. Production deployment would need ACLs, TLS, private networking, validation of preference values and a recovery plan.

[4] Redis. *Redis hashes*. https://redis.io/docs/latest/develop/data-types/hashes/

[5] Redis. *Redis persistence*. https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/

[8] Redis. *Scripting with Lua*. https://redis.io/docs/latest/develop/programmability/eval-intro/

## Reproduce this activity

The evidence above was regenerated on 12 November 2026. Follow the complete-lab commands in the root README; they create isolated services and run the activities in dependency order. Do not rerun the transaction fixture loader on an already populated lab.
