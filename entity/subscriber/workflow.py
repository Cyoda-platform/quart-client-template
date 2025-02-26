async def process_lower_subscription_type(entity: dict):
    # Lowercase the subscriptionType if it exists and is a string.
    if "subscriptionType" in entity and isinstance(entity["subscriptionType"], str):
        entity["subscriptionType"] = entity["subscriptionType"].lower()

async def process_trim_callback_url(entity: dict):
    # Trim the callbackUrl if it exists and is a string.
    if "callbackUrl" in entity and isinstance(entity["callbackUrl"], str):
        entity["callbackUrl"] = entity["callbackUrl"].strip()