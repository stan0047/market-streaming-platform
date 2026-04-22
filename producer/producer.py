import json
import time
import random
import logging
from datetime import datetime
from kafka import KafkaProducer
from kafka.errors import KafkaError
import yfinance as yf
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.kafka_config import (
    KAFKA_BROKER, KAFKA_TOPIC, STOCK_SYMBOLS, PRODUCE_INTERVAL_SECONDS
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def create_producer():
    """Create Kafka producer with retry logic."""
    retries = 5
    for attempt in range(retries):
        try:
            producer = KafkaProducer(
                bootstrap_servers=["127.0.0.1:9092"],  # force IPv4
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                acks="all",
                retries=3,
                max_block_ms=10000,
                request_timeout_ms=15000,
                connections_max_idle_ms=60000,
            )
            logger.info(f"Connected to Kafka at {KAFKA_BROKER}")
            return producer
        except Exception as e:
            logger.warning(f"Attempt {attempt+1}/{retries} failed: {e}")
            time.sleep(3)
    raise RuntimeError("Could not connect to Kafka after retries")


def fetch_stock_data(symbol: str) -> dict:
    """
    Fetch latest stock price from Yahoo Finance.
    Falls back to simulated data if API is unavailable.
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info

        price = round(float(info.last_price), 2)
        prev_close = round(float(info.previous_close), 2)
        change_pct = round(((price - prev_close) / prev_close) * 100, 4)

        return {
            "symbol": symbol,
            "price": price,
            "previous_close": prev_close,
            "change_pct": change_pct,
            "volume": int(info.three_month_average_volume or 0),
            "market_cap": int(info.market_cap or 0),
            "timestamp": datetime.utcnow().isoformat(),
            "source": "live"
        }

    except Exception as e:
        logger.warning(f"Live fetch failed for {symbol}, using simulated data: {e}")
        return simulate_stock_data(symbol)


def simulate_stock_data(symbol: str) -> dict:
    """Generate realistic simulated stock data."""
    base_prices = {
        "AAPL": 175.0, "GOOGL": 140.0, "MSFT": 380.0,
        "AMZN": 185.0, "TSLA": 175.0, "META": 500.0,
        "NVDA": 870.0, "JPM": 195.0
    }
    base = base_prices.get(symbol, 100.0)
    price = round(base * (1 + random.uniform(-0.02, 0.02)), 2)
    prev_close = round(base * (1 + random.uniform(-0.01, 0.01)), 2)
    change_pct = round(((price - prev_close) / prev_close) * 100, 4)

    return {
        "symbol": symbol,
        "price": price,
        "previous_close": prev_close,
        "change_pct": change_pct,
        "volume": random.randint(1_000_000, 50_000_000),
        "market_cap": random.randint(500_000_000, 3_000_000_000_000),
        "timestamp": datetime.utcnow().isoformat(),
        "source": "simulated"
    }


def on_success(metadata):
    logger.info(
        f"Sent to topic={metadata.topic} "
        f"partition={metadata.partition} "
        f"offset={metadata.offset}"
    )


def on_error(e):
    logger.error(f"Failed to send message: {e}")


def run_producer():
    """Main producer loop — publishes stock events continuously."""
    producer = create_producer()
    events_sent = 0
    start_time = time.time()

    logger.info(f"Starting producer for symbols: {STOCK_SYMBOLS}")
    logger.info(f"Publishing to topic: {KAFKA_TOPIC}")

    try:
        while True:
            for symbol in STOCK_SYMBOLS:
                data = fetch_stock_data(symbol)

                producer.send(
                    KAFKA_TOPIC,
                    key=symbol.encode("utf-8"),
                    value=data
                ).add_callback(on_success).add_errback(on_error)

                events_sent += 1

            producer.flush()

            # Log throughput every 10 rounds
            elapsed = time.time() - start_time
            rate = round(events_sent / elapsed * 60, 0)
            logger.info(
                f"Total events sent: {events_sent} | "
                f"Rate: ~{rate} events/min | "
                f"Uptime: {round(elapsed)}s"
            )

            time.sleep(PRODUCE_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        logger.info("Producer stopped by user.")
    finally:
        producer.close()
        logger.info(f"Final count: {events_sent} events sent.")


if __name__ == "__main__":
    run_producer()