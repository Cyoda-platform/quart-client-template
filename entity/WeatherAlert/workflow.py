import asyncio

async def isValidAlertInput(entity: dict) -> bool:
    latitude = entity.get("location", {}).get("latitude")
    longitude = entity.get("location", {}).get("longitude")
    conditions = entity.get("conditions")
    if latitude is None or longitude is None or conditions is None:
        entity["success"] = False
        return False
    if not isinstance(conditions, dict):
        entity["success"] = False
        return False
    entity["success"] = True
    return True

async def isNotValidAlertInput(entity: dict) -> bool:
    valid = await isValidAlertInput(entity)
    entity["success"] = not valid
    return not valid

async def evaluateAlertConditions(entity: dict):
    entity["evaluationInProgress"] = True
    entity["workflowProcessed"] = False
    # Placeholder for actual evaluation logic; will be done in areConditionsMet or areConditionsNotMet
    await asyncio.sleep(0)
    return entity

async def areConditionsMet(entity: dict) -> bool:
    forecast = entity.get("forecast")
    conditions = entity.get("conditions", {})
    if not forecast or not conditions:
        entity["success"] = False
        return False
    temperature_threshold = conditions.get("temperature_threshold", {})
    rain_forecast_required = conditions.get("rain_forecast", False)

    temp_above = temperature_threshold.get("above")
    temp_below = temperature_threshold.get("below")

    temperature = None
    # Extract temperature from forecast if available (example logic)
    daily = forecast.get("daily", {})
    temperatures = daily.get("temperature_2m_max") or daily.get("temperature_2m")
    if isinstance(temperatures, list) and temperatures:
        temperature = temperatures[0]

    rain = None
    precipitation = daily.get("precipitation_sum")
    if isinstance(precipitation, list) and precipitation:
        rain = precipitation[0]

    temp_ok = True
    if temperature is not None:
        if temp_above is not None and temperature <= temp_above:
            temp_ok = False
        if temp_below is not None and temperature >= temp_below:
            temp_ok = False

    rain_ok = True
    if rain_forecast_required:
        rain_ok = rain is not None and rain > 0

    alert_triggered = temp_ok and rain_ok

    entity["alert_status"] = "triggered" if alert_triggered else "not_triggered"
    entity["success"] = alert_triggered
    entity["workflowProcessed"] = True
    return alert_triggered

async def areConditionsNotMet(entity: dict) -> bool:
    met = await areConditionsMet(entity)
    not_met = not met
    entity["success"] = not_met
    return not_met

async def setAlertTriggered(entity: dict):
    entity["alert_status"] = "triggered"
    entity["workflowProcessed"] = True
    return entity

async def setAlertNotTriggered(entity: dict):
    entity["alert_status"] = "not_triggered"
    entity["workflowProcessed"] = True
    return entity

async def notifyUser(entity: dict):
    # Template for notification logic, e.g., send email or push notification
    entity["notification_sent"] = True
    entity["workflowProcessed"] = True
    return entity