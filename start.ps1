# ── Market Streaming Platform v2 - Startup Guide ──────────────

Write-Host "=================================================" -ForegroundColor Cyan
Write-Host " Market Streaming Platform v2" -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "This project runs on AWS EC2 (v2)." -ForegroundColor Yellow
Write-Host "Use the commands below to start the platform." -ForegroundColor Yellow
Write-Host ""

Write-Host "── STEP 1: SSH into EC2 ─────────────────────────" -ForegroundColor Green
Write-Host "  ssh -i C:\Users\<you>\.ssh\market-key.pem ubuntu@<EC2_PUBLIC_IP>" -ForegroundColor White
Write-Host ""

Write-Host "── STEP 2: Start Docker stack ───────────────────" -ForegroundColor Green
Write-Host "  cd ~/market-streaming-platform" -ForegroundColor White
Write-Host "  source venv/bin/activate" -ForegroundColor White
Write-Host "  docker-compose up -d" -ForegroundColor White
Write-Host ""

Write-Host "── STEP 3: Terminal 1 — Producer ────────────────" -ForegroundColor Green
Write-Host "  python producer/producer.py" -ForegroundColor White
Write-Host ""

Write-Host "── STEP 4: Terminal 2 — Spark Consumer ──────────" -ForegroundColor Green
Write-Host "  python consumer/spark_consumer.py" -ForegroundColor White
Write-Host ""

Write-Host "── STEP 5: Terminal 3 — Airflow ─────────────────" -ForegroundColor Green
Write-Host "  export AIRFLOW_HOME=~/market-streaming-platform/airflow" -ForegroundColor White
Write-Host "  airflow webserver -p 8080 -D" -ForegroundColor White
Write-Host "  airflow scheduler -D" -ForegroundColor White
Write-Host ""

Write-Host "── STEP 6: dbt + Data Quality ───────────────────" -ForegroundColor Green
Write-Host "  dbt run --project-dir dbt/ --profiles-dir dbt/" -ForegroundColor White
Write-Host "  python great_expectations/dq_suite.py" -ForegroundColor White
Write-Host ""

Write-Host "── ACCESS POINTS ────────────────────────────────" -ForegroundColor Cyan
Write-Host "  Grafana:  http://<EC2_IP>:3000  (admin/admin)" -ForegroundColor White
Write-Host "  Airflow:  http://<EC2_IP>:8080  (admin/admin)" -ForegroundColor White
Write-Host ""

Write-Host "── SHUTDOWN (saves data) ────────────────────────" -ForegroundColor Red
Write-Host "  docker-compose down" -ForegroundColor White
Write-Host "  Then STOP EC2 in AWS Console to avoid charges." -ForegroundColor White
Write-Host "=================================================" -ForegroundColor Cyan
