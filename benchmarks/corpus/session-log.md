I spent the session tracing memory growth in the ingest worker.

The worker lives in services/ingest/src/worker/consumer.go. It opens a new
decoder per message and never closes it. The decoder holds a 4MB buffer, so
throughput of 200 messages per second grows the heap quickly. I confirmed this
with a heap profile: the decoder buffer accounts for 87 percent of live objects.

The same consumer is reused by services/ingest/src/worker/replay.go, which
replays archived batches. That path has the same leak but runs rarely, so it
was never noticed.

I checked services/ingest/src/pool/bufferPool.go. A pool already exists and is
used by the HTTP path, but the worker never calls into it. So the fix is to
route the worker decoder through the existing pool rather than writing anything
new.

I tried simply closing the decoder after each message. That fixed the leak but
cost 12 percent throughput because allocation dominates. I reverted it.

The correct fix is to acquire a decoder from the pool and release it back. That
requires changing the consumer loop and the replay loop.

This is on the hot ingest path so it needs a load test before merging. The
owner of the ingest service is the data platform team.

I am not sure whether the leak affects production memory limits yet. The worker
restarts every six hours, which probably masks it. Someone should check whether
restart frequency correlates with deploy size.

Do not rename the metric "ingest_decoder_live_bytes" because the dashboard and
two alerts query it by exact name.
