import psycopg2
import json
import boto3
from datetime import datetime

PG = dict(host='localhost', port=5432, dbname='market_db',
          user='market_user', password='market_pass')

def run_checks():
    conn = psycopg2.connect(**PG)
    cur  = conn.cursor()
    results = []

    def check(name, query, assertion, msg):
        cur.execute(query)
        val = cur.fetchone()[0]
        passed = assertion(val)
        results.append({"check": name, "value": str(val),
                        "status": "PASS" if passed else "FAIL", "msg": msg})
        return passed

    # 1. Schema — required columns exist
    check("schema_columns",
          "SELECT COUNT(*) FROM information_schema.columns WHERE table_name='stock_metrics' AND column_name IN ('symbol','price','volume','event_time')",
          lambda v: v == 4, "All 4 required columns present")

    # 2. No null symbols
    check("no_null_symbols",
          "SELECT COUNT(*) FROM stock_metrics WHERE symbol IS NULL",
          lambda v: v == 0, "No null symbols")

    # 3. Price range $1–$100,000
    check("price_range",
          "SELECT COUNT(*) FROM stock_metrics WHERE price <= 0 OR price > 100000",
          lambda v: v == 0, "All prices in valid range")

    # 4. Volume non-negative
    check("volume_positive",
          "SELECT COUNT(*) FROM stock_metrics WHERE volume < 0",
          lambda v: v == 0, "All volumes non-negative")

    # 5. Freshness — data within last 2 hours
    check("data_freshness",
          "SELECT EXTRACT(EPOCH FROM (NOW() - MAX(processed_at)))/3600 FROM stock_metrics",
          lambda v: float(v) < 2, "Data is fresh (< 2 hours old)")

    # 6. Min row count
    check("min_row_count",
          "SELECT COUNT(*) FROM stock_metrics",
          lambda v: v >= 10, "At least 10 rows in table")

    # 7. All 50 symbols present in mart
    check("symbol_coverage",
          "SELECT COUNT(DISTINCT symbol) FROM mart_symbol_daily",
          lambda v: v >= 40, "At least 40 symbols in mart")

    conn.close()

    passed = sum(1 for r in results if r['status'] == 'PASS')
    total  = len(results)
    report = {
        "run_time": datetime.utcnow().isoformat(),
        "summary": f"{passed}/{total} checks passed",
        "status": "PASS" if passed == total else "FAIL",
        "checks": results
    }

    print(json.dumps(report, indent=2))

    # Save to S3
    try:
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.put_object(
            Bucket='market-streaming-data-aayus',
            Key=f"dq_reports/ge_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json",
            Body=json.dumps(report)
        )
        print("DQ report saved to S3")
    except Exception as e:
        print(f"S3 upload skipped: {e}")

    return report

if __name__ == "__main__":
    run_checks()
