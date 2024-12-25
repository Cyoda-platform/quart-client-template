import requests

API_URL = "https://api.opendata.esett.com"


def get_balance_responsible_parties(code=None, country=None, name=None):
    params = {}
    if code:
        params["code"] = code
    if country:
        params["country"] = country
    if name:
        params["name"] = name
    response = requests.get(f"{API_URL}/EXP01/BalanceResponsibleParties", params=params)
    return response.json() if response.status_code == 200 else response.text


def ingest_data(code=None, country=None, name=None):
    data = get_balance_responsible_parties(code, country, name)
    print("Retrieved Data:", data)
    return data


def main():
    # Example test call to ingest_data
    print("Testing ingest_data function...")
    ingest_data(code="some_code", country="FI", name="some_name")


if __name__ == "__main__":
    main()
