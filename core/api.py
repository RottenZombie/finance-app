import requests

API = "https://open.er-api.com/v6/latest"


def get_all_rates():
    try:
        data = requests.get(f"{API}/USD", timeout=5).json()
        rates = data.get("rates", {})
        usd_try = rates.get("TRY")

        return {
            "USD": usd_try,
            "EUR": usd_try / rates.get("EUR") if rates.get("EUR") else None,
            "HUF": usd_try / rates.get("HUF") if rates.get("HUF") else None,
            "status": "Online"
        }
    except:
        return {"USD": None, "EUR": None, "HUF": None, "status": "Offline"}


def get_metal_prices():
    try:
        gold = requests.get("https://api.gold-api.com/price/XAU", timeout=5).json()
        silver = requests.get("https://api.gold-api.com/price/XAG", timeout=5).json()

        print("GOLD RAW:", gold)
        print("SILVER RAW:", silver)

        gold_price = gold.get("price", 0)
        silver_price = silver.get("price", 0)

        return gold_price, silver_price

    except Exception as e:
        print("METAL API ERROR:", e)
        return 0, 0