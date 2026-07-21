CREATE TABLE IF NOT EXISTS default.initial_events_local ON CLUSTER ugc_cluster
(
    user_id UInt32,
    category String,
    amount Float64,
    status String,
    region String,
    timestamp DateTime
)
ENGINE = ReplicatedMergeTree('/clickhouse/tables/{shard}/default/initial_events_local', '{replica}')
ORDER BY (timestamp, category);

CREATE TABLE IF NOT EXISTS default.events_local ON CLUSTER ugc_cluster
(
    user_id UInt32,
    category String,
    amount Float64,
    status String,
    region String,
    timestamp DateTime
)
ENGINE = ReplicatedMergeTree('/clickhouse/tables/{shard}/default/events_local', '{replica}')
ORDER BY (timestamp, category);

CREATE TABLE IF NOT EXISTS default.initial_events ON CLUSTER ugc_cluster
AS default.initial_events_local
ENGINE = Distributed('ugc_cluster', 'default', 'initial_events_local', cityHash64(user_id));

CREATE TABLE IF NOT EXISTS default.events ON CLUSTER ugc_cluster
AS default.events_local
ENGINE = Distributed('ugc_cluster', 'default', 'events_local', cityHash64(user_id));
