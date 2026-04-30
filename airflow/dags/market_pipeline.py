from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta
import boto3
import psycopg2
import json
import os

default_args = {
    'owner': 'market',
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
}

PG = dict(host='localhost', port=5432, dbname='market_db',
          user='market_user', password='market_pass')

# ── DAG 1: symbol_refresh (daily) ──────────────────────────────
def refresh_symbols():
    from config.kafka_config import STOCK_SYMBOLS
    s3 = boto3.client('s3', region_name='us-east-1')
    s3.put_object(
        Bucket='market-streaming-data-aayus',
        Key='config/symbols.json',
        Body=json.dumps({'symbols': STOCK_SYMBOLS, 'updated': datetime.utcnow().isoformat()})
    )
    print(f"Uploaded {len(STOCK_SYMBOLS)} symbols to S3")

with DAG('symbol_refresh', default_args=default_args,
         schedule_interval='@daily', start_date=datetime(2026,1,1),
         catchup=False, tags=['market']) as dag1:
    PythonOperator(task_id='upload_symbols_to_s3', python_callable=refresh_symbols)

# ── DAG 2: dbt_run (hourly) ────────────────────────────────────
with DAG('dbt_run', default_args=default_args,
         schedule_interval='@hourly', start_date=datetime(2026,1,1),
         catchup=False, tags=['market']) as dag2:
    BashOperator(
        task_id='dbt_run_models',
        bash_command='cd ~/market-streaming-platform && source venv/bin/activate && dbt run --project-dir dbt/ --profiles-dir dbt/ 2>&1 || echo "dbt not configured yet"',
    )

# ── DAG 3: dq_checks (hourly) ─────────────────────────────────
def run_dq_checks():
    conn = psycopg2.connect(**PG)
    cur  = conn.cursor()
    errors = []

    # Check 1: no nulls in symbol
    cur.execute("SELECT COUNT(*) FROM stock_metrics WHERE symbol IS NULL")
    nulls = cur.fetchone()[0]
    if nulls > 0:
        errors.append(f"NULL symbols: {nulls}")

    # Check 2: price in valid range
    cur.execute("SELECT COUNT(*) FROM stock_metrics WHERE price <= 0 OR price > 100000")
    bad_prices = cur.fetchone()[0]
    if bad_prices > 0:
        errors.append(f"Bad prices: {bad_prices}")

    # Check 3: freshness — data in last 2 hours
    cur.execute("SELECT MAX(processed_at) FROM stock_metrics")
    latest = cur.fetchone()[0]
    if latest:
        age = (datetime.utcnow() - latest.replace(tzinfo=None)).seconds / 3600
        if age > 2:
            errors.append(f"Stale data: last record {age:.1f}h ago")

    # Check 4: row count
    cur.execute("SELECT COUNT(*) FROM stock_metrics")
    total = cur.fetchone()[0]

    conn.close()
    result = {'total_rows': total, 'errors': errors, 'status': 'PASS' if not errors else 'FAIL'}
    print(json.dumps(result, indent=2))

    # Save DQ report to S3
    s3 = boto3.client('s3', region_name='us-east-1')
    s3.put_object(
        Bucket='market-streaming-data-aayus',
        Key=f"dq_reports/{datetime.utcnow().strftime('%Y/%m/%d/%H%M')}.json",
        Body=json.dumps(result)
    )
    if errors:
        raise ValueError(f"DQ checks failed: {errors}")

with DAG('dq_checks', default_args=default_args,
         schedule_interval='@hourly', start_date=datetime(2026,1,1),
         catchup=False, tags=['market']) as dag3:
    PythonOperator(task_id='run_data_quality_checks', python_callable=run_dq_checks)

# ── DAG 4: s3_export (nightly) ────────────────────────────────
def export_to_s3():
    conn = psycopg2.connect(**PG)
    cur  = conn.cursor()
    cur.execute("""
        SELECT symbol, price, previous_close, change_pct,
               volume, market_cap, event_time, source
        FROM stock_metrics
        WHERE processed_at >= NOW() - INTERVAL '24 hours'
        ORDER BY event_time
    """)
    rows = cur.fetchall()
    cols = ['symbol','price','previous_close','change_pct',
            'volume','market_cap','event_time','source']
    records = []
    for row in rows:
        r = dict(zip(cols, row))
        r['event_time'] = r['event_time'].isoformat() if r['event_time'] else None
        records.append(r)
    conn.close()

    s3 = boto3.client('s3', region_name='us-east-1')
    date_str = datetime.utcnow().strftime('%Y/%m/%d')
    s3.put_object(
        Bucket='market-streaming-data-aayus',
        Key=f"processed/{date_str}/daily_export.json",
        Body=json.dumps(records)
    )
    print(f"Exported {len(records)} rows to S3 processed layer")

with DAG('s3_export', default_args=default_args,
         schedule_interval='0 1 * * *', start_date=datetime(2026,1,1),
         catchup=False, tags=['market']) as dag4:
    PythonOperator(task_id='export_daily_to_s3', python_callable=export_to_s3)
