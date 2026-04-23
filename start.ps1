# ── Market Streaming Platform - One-Click Startup ──────────
Write-Host "Starting Market Streaming Platform..." -ForegroundColor Cyan

# Set Hadoop for Spark
$env:HADOOP_HOME = "C:\hadoop"
$env:PATH = "$env:PATH;C:\hadoop\bin"

# Activate venv
.\venv\Scripts\Activate.ps1

# Start Docker containers
Write-Host "Starting Docker containers..." -ForegroundColor Yellow
docker-compose up -d

# Wait for containers to be ready
Write-Host "Waiting for containers to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 25

# Show container status
docker-compose ps

# Recreate DB table if it doesn't exist
Write-Host "Ensuring database table exists..." -ForegroundColor Yellow
docker exec postgres psql -U market_user -d market_db -c "
CREATE TABLE IF NOT EXISTS stock_metrics (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    price DECIMAL(10,2),
    previous_close DECIMAL(10,2),
    change_pct DECIMAL(8,4),
    volume BIGINT,
    market_cap BIGINT,
    event_time TIMESTAMP,
    processed_at TIMESTAMP DEFAULT NOW(),
    source VARCHAR(20)
);
CREATE INDEX IF NOT EXISTS idx_symbol ON stock_metrics(symbol);
CREATE INDEX IF NOT EXISTS idx_event_time ON stock_metrics(event_time);
" 2>$null

Write-Host ""
Write-Host "=====================================" -ForegroundColor Green
Write-Host " Setup complete! Now open 2 more terminals and run:" -ForegroundColor Green
Write-Host ""
Write-Host " Terminal 1 - Producer:" -ForegroundColor Cyan
Write-Host "   .\venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "   python producer/producer.py" -ForegroundColor White
Write-Host ""
Write-Host " Terminal 2 - Spark Consumer:" -ForegroundColor Cyan
Write-Host "   .\venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "   `$env:HADOOP_HOME = 'C:\hadoop'" -ForegroundColor White
Write-Host "   `$env:PATH = `"`$env:PATH;C:\hadoop\bin`"" -ForegroundColor White
Write-Host "   python consumer/spark_consumer.py" -ForegroundColor White
Write-Host ""
Write-Host " Grafana: http://localhost:3000 (admin/admin)" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Green