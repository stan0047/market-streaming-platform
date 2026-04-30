![Python](https://img.shields.io/badge/Python-3.10-blue?logo=python)
![Kafka](https://img.shields.io/badge/Apache%20Kafka-7.4.0-black?logo=apachekafka)
![Spark](https://img.shields.io/badge/Apache%20Spark-3.5-orange?logo=apachespark)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue?logo=postgresql)
![Airflow](https://img.shields.io/badge/Apache%20Airflow-2.8.1-017CEE?logo=apacheairflow)
![dbt](https://img.shields.io/badge/dbt-1.7.0-FF694B?logo=dbt)
![AWS](https://img.shields.io/badge/AWS-EC2%20%2B%20S3-FF9900?logo=amazonaws)
![Grafana](https://img.shields.io/badge/Grafana-10.2-orange?logo=grafana)
![Docker](https://img.shields.io/badge/Docker-Compose-blue?logo=docker)
![License](https://img.shields.io/badge/License-MIT-green)

# Real-Time Market Data Streaming Platform — v2

A cloud-native, production-grade real-time streaming pipeline deployed on AWS EC2, processing 5,000+ stock market events per minute across 50+ symbols.

![Architecture](docs/architecture.png)
![Dashboard](docs/dashboard.png)

## What's New in v2

| Feature | v1 | v2 |
|---|---|---|
| Deployment | Local Windows | AWS EC2 t3.micro |
| Symbols | 8 | 50+ (S&P 500) |
| Storage | PostgreSQL only | PostgreSQL + S3 |
| Orchestration | None | Apache Airflow (4 DAGs) |
| Transformation | None | dbt Core (staging + mart) |
| Data Quality | None | Great Expectations (7 checks) |
| Cost | $0 local | ~$0 (AWS free tier) |

## Architecture
## Tech Stack

| Layer | Technology |
|---|---|
| Data Source | Yahoo Finance (yfinance) |
| Message Broker | Apache Kafka 7.4.0 |
| Stream Processor | Spark Structured Streaming 3.5 |
| Storage — Hot | PostgreSQL 15 (Docker) |
| Storage — Cold | AWS S3 (JSON + Parquet) |
| Transformation | dbt Core 1.7 |
| Data Quality | Great Expectations (7 checks) |
| Orchestration | Apache Airflow 2.8.1 |
| Visualization | Grafana 10.2 |
| Infrastructure | AWS EC2 t3.micro + Docker Compose |

## Airflow DAGs

| DAG | Schedule | Purpose |
|---|---|---|
| symbol_refresh | Daily | Upload S&P 500 symbols to S3 |
| dbt_run | Hourly | Refresh staging + mart models |
| dq_checks | Hourly | Run 7-check GE suite → S3 report |
| s3_export | Nightly | Export 24h data to S3 processed layer |

## dbt Models

- **stg_stock_metrics** (view) — cleaned source with direction flag (up/down/flat)
- **mart_symbol_daily** (table) — daily OHLCV aggregations per symbol

## Data Quality Checks (7/7 Passing)

1. Schema — all required columns present
2. No null symbols
3. Price range $1–$100,000
4. Volume non-negative
5. Data freshness < 2 hours
6. Minimum row count >= 10
7. Symbol coverage >= 40 symbols in mart

## S3 Structure
## Quick Start (EC2)

```bash
ssh -i market-key.pem ubuntu@<EC2_IP>
cd ~/market-streaming-platform
source venv/bin/activate
docker-compose up -d

# Terminal 1
python producer/producer.py

# Terminal 2
python consumer/spark_consumer.py

# Terminal 3 — Airflow
export AIRFLOW_HOME=~/market-streaming-platform/airflow
airflow webserver -p 8080 -D && airflow scheduler -D

# Run dbt + DQ
dbt run --project-dir dbt/ --profiles-dir dbt/
python great_expectations/dq_suite.py
```

## Performance

| Metric | Value |
|---|---|
| Throughput | 5,000+ events/min |
| Symbols | 50+ (S&P 500) |
| Latency | ~10 seconds end-to-end |
| DQ checks | 7/7 passing |
| AWS cost | ~$0/month (free tier) |

## License
MIT
