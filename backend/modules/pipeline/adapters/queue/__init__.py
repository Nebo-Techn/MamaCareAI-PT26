"""
Queue adapters (PDF section 2, section 4).

    memory  -> tests and single-process local runs
    sqlite  -> multi-process on one machine, still free
    sqs     -> production, managed, no ops
    kafka   -> only if throughput genuinely demands it

CHOOSE THE SMALLEST THING THAT WORKS. Kafka is in the design doc as an option,
not a requirement — it is a serious operational commitment (brokers, consumer
groups, partition rebalancing) that pays off at high throughput and costs a lot
of attention below it. PDF section 6 flags expected volume as an open question;
until it is answered, SQS or the SQLite queue is the right default, and the
port means switching later is a config change.
"""
