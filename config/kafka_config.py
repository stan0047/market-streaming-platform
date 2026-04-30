import os
from dotenv import load_dotenv
load_dotenv()

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "127.0.0.1:9092")
KAFKA_TOPIC  = os.getenv("KAFKA_TOPIC",  "market_data")

STOCK_SYMBOLS = [
    # Tech
    "AAPL","MSFT","NVDA","GOOGL","META","AMZN","TSLA","AVGO","ORCL","AMD",
    "INTC","QCOM","TXN","MU","AMAT","ADBE","CRM","NOW","SNPS","KLAC",
    # Finance
    "JPM","BAC","WFC","GS","MS","BLK","SCHW","AXP","COF","USB",
    # Healthcare
    "UNH","JNJ","LLY","ABBV","MRK","TMO","ABT","DHR","BMY","AMGN",
    # Consumer / Retail
    "WMT","HD","MCD","NKE","SBUX","TGT","COST","LOW","TJX","PG",
    # Energy / Industrial
    "XOM","CVX","NEE","CAT","BA","GE","MMM","HON","UPS","DE",
]

PRODUCE_INTERVAL_SECONDS = 2  # slightly slower to handle 50 symbols
