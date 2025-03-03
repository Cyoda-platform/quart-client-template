import asyncio
from datetime import datetime
import httpx

# Process conversion rates by fetching BTC/USD and BTC/EUR prices and updating the entity.
async def process_fetch_conversion_rates(entity: dict) -> None:
    # Internal helper to fetch the conversion rate for a given symbol.
    async def _fetch_rate(symbol: str) -> float:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url)
            response.raise_for_status()  # Raise error for non-200 responses
            data = response.json()
            try:
                price = float(data.get("price", 0.0))
            except (TypeError, ValueError):
                raise ValueError(f"Invalid price received for {symbol}: {data.get('price')}")
            return price
    btc_usd = await _fetch_rate("BTCUSDT")
    btc_eur = await _fetch_rate("BTCEUR")
    entity["conversionRates"] = {"BTC_USD": btc_usd, "BTC_EUR": btc_eur}

# Process sending an email by using the entity's recipient, conversion rates, and timestamp.
async def process_send_email(entity: dict) -> None:
    # Simulate sending email (replace with actual integration if needed).
    # The email payload consists of conversion rates and timestamp from the entity.
    report = {
        "conversionRates": entity["conversionRates"],
        "timestamp": entity["timestamp"]
    }
    print(f"Sending email to {entity['recipient']} with report: {report}")
    await asyncio.sleep(0.1)