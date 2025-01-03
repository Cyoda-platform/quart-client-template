import requests

BASE_URL = "https://api.example.com/data"


def get_user_feedback(params):
    response = requests.get(f"{BASE_URL}/feedback", params=params)
    response.raise_for_status()  # Raise an error for bad responses
    return response.json()


def analyze_sentiment(data):
    response = requests.post(f"{BASE_URL}/feedback/sentiment", json=data)
    response.raise_for_status()  # Raise an error for bad responses
    return response.json()


def generate_summary_report():
    response = requests.get(f"{BASE_URL}/feedback/report")
    response.raise_for_status()  # Raise an error for bad responses
    return response.json()


def ingest_data(feedback_params, sentiment_data):
    feedback = get_user_feedback(feedback_params)
    sentiment_analysis = analyze_sentiment(sentiment_data)
    summary_report = generate_summary_report()
    return feedback, sentiment_analysis, summary_report


if __name__ == "__main__":
    feedback_params = {"param1": "value1", "param2": "value2"}
    sentiment_data = {"comments": ["Great service!", "Will come back again."]}
    feedback, sentiment_analysis, summary_report = ingest_data(
        feedback_params, sentiment_data
    )
    print("Feedback:", feedback)
    print("Sentiment Analysis:", sentiment_analysis)
    print("Summary Report:", summary_report)
