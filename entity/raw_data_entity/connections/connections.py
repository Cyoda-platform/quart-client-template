import requests

BASE_URL = "https://api.opendata.esett.com"


def get_balance_responsible_parties(code=None, country=None, name=None):
    params = {"code": code, "country": country, "name": name}
    response = requests.get(
        f"{BASE_URL}/EXP01/BalanceResponsibleParties", params=params
    )
    return response.json()


def ingest_data(code=None, country=None, name=None):
    return get_balance_responsible_parties(code, country, name)


if __name__ == "__main__":
    test_data = ingest_data(country="FI")
    print(test_data)
