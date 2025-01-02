import requests

API_BASE_URL = "https://virtserver.swaggerhub.com/VICTORIASAGDIEVA_1/feedback/1.0.0"


def get_user_feedback():
    """Fetch user feedback from the API."""
    response = requests.get(f"{API_BASE_URL}/feedback")
    if response.status_code == 200:
        return response.json()
    else:
        response.raise_for_status()


def analyze_sentiment(comments):
    """Analyze sentiment of user feedback comments."""
    response = requests.post(
        f"{API_BASE_URL}/feedback/sentiment", json={"comments": comments}
    )
    if response.status_code == 200:
        return response.json()
    else:
        response.raise_for_status()


def generate_summary_report():
    """Generate a summary report of user feedback."""
    response = requests.get(f"{API_BASE_URL}/feedback/report")
    if response.status_code == 200:
        return response.json()
    else:
        response.raise_for_status()


def ingest_data():
    """Ingest data by fetching user feedback, analyzing sentiment, and generating a report."""
    feedback_data = get_user_feedback()
    sentiment_results = analyze_sentiment(
        [feedback["comment"] for feedback in feedback_data]
    )
    summary_report = generate_summary_report()
    return feedback_data, sentiment_results, summary_report


def main():
    try:
        feedback_data, sentiment_results, summary_report = ingest_data()
        print("Feedback Data:", feedback_data)
        print("Sentiment Results:", sentiment_results)
        print("Summary Report:", summary_report)
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
