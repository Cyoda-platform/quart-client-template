import logging
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "https://api.opendata.esett.com"


def get_balance_responsible_parties(code=None, country=None, name=None):
    params = {"code": code, "country": country, "name": name}
    response = requests.get(
        f"{BASE_URL}/EXP01/BalanceResponsibleParties", params=params
    )
    if response.status_code == 200:
        return response.json()
    else:
        logger.error(f"Failed to fetch data: {response.status_code}")
        return None


def ingest_data(code=None, country=None, name=None):
    data = get_balance_responsible_parties(code, country, name)
    logger.info(data)
    return data


def main():
    data = ingest_data(code="579000282425", country="", name="")
    print(data)


if __name__ == "__main__":
    main()
