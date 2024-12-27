import requests

# Function to get Balance Responsible Parties


def get_balance_responsible_parties(code=None, country=None, name=None):
    url = "https://api.opendata.esett.com/EXP01/BalanceResponsibleParties"
    params = {}
    if code:
        params["code"] = code
    if country:
        params["country"] = country
    if name:
        params["name"] = name
    response = requests.get(url, params=params)
    return response.text


# Public function to ingest data


def ingest_data(code=None, country=None, name=None):
    data = get_balance_responsible_parties(code, country, name)
    return data


# Main method for testing


def main():
    code = "BRP123"
    country = "FI"
    name = None
    data = ingest_data(code, country, name)
    print(data)


if __name__ == "__main__":
    main()
