import requests

BASE_URL = "https://api.opendata.esett.com"


def get_balance_responsible_parties(code=None, country=None, name=None):
    params = {}
    if code:
        params["code"] = code
    if country:
        params["country"] = country
    if name:
        params["name"] = name
    response = requests.get(
        f"{BASE_URL}/EXP01/BalanceResponsibleParties", params=params
    )
    return response.json()


def ingest_data(code=None, country=None, name=None):
    data = get_balance_responsible_parties(code, country, name)
    return data


if __name__ == "__main__":
    # Test the ingest_data function
    test_data = ingest_data(code="BRP123", country="FI", name="Some BRP")
    print(test_data)
