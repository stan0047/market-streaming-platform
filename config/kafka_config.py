import os
from dotenv import load_dotenv

load_dotenv()

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "127.0.0.1:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "market_data")

STOCK_SYMBOLS = [
    "AAPL",  # Apple
    "GOOGL", # Google
    "MSFT",  # Microsoft
    "AMZN",  # Amazon
    "TSLA",  # Tesla
    "META",  # Meta
    "NVDA",  # Nvidia
    "JPM",   # JPMorgan
]

PRODUCE_INTERVAL_SECONDS = 1