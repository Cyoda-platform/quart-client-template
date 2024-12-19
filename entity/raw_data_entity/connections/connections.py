import requests

BASE_URL = 'https://api.opendata.esett.com'


def get_balance_responsible_parties(code=None, country=None, name=None):
    params = {}
    if code:
        params['code'] = code
    if country:
        params['country'] = country
    if name:
        params['name'] = name
    response = requests.get(f'{BASE_URL}/EXP01/BalanceResponsibleParties', params=params)
    return response.json() if response.status_code == 200 else response.text


def ingest_data(code=None, country=None, name=None):
    data = get_balance_responsible_parties(code, country, name)
    return data


def main():
    # Example usage of ingest_data function
    result = ingest_data(code='BRP123', country='FI', name='Example BRP')
    print(result)


if __name__ == '__main__':
    main()