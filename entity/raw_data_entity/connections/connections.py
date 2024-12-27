import requests

BASE_URL = "https://api.opendata.esett.com"


def get_balance_responsible_parties(code=None, country=None, name=None):
    url = f"{BASE_URL}/EXP01/BalanceResponsibleParties"
    params = {}
    if code:
        params["code"] = code
    if country:
        params["country"] = country
    if name:
        params["name"] = name
    response = requests.get(url, params=params)
    return response.json()


def ingest_data(code=None, country=None, name=None):
    data = get_balance_responsible_parties(code, country, name)
    return data


if __name__ == "__main__":
    # Example test
    result = ingest_data(code="BRP123", country="FI", name="Example BRP")
    print(result)
