import requests


def get_data_from_endpoint_1(param1, param2):
    response = requests.get(
        f"http://test.com/endpoint1?param1={param1}&param2={param2}"
    )
    return response.text


def get_data_from_endpoint_2(param1):
    response = requests.get(f"http://test.com/endpoint2?param1={param1}")
    return response.text


def ingest_data(param1, param2):
    data1 = get_data_from_endpoint_1(param1, param2)
    data2 = get_data_from_endpoint_2(param1)
    return data1, data2


if __name__ == "__main__":
    result = ingest_data("value1", "value2")
    print(result)
