# Subscriber Notification Message Implementation

## Overview

This document summarizes the implementation of a new `subscriber_notification_message` entity that encapsulates individual notification messages to subscribers with resend and cancellation capabilities. The implementation also modifies the existing `fetch_request` workflow to create these notification entities instead of directly sending emails.

## Problem Statement

The original system had a monolithic approach where the `fetch_request` workflow would:
1. Fetch NBA scores
2. Directly send email notifications to all subscribers in a single process

This approach had limitations:
- No retry mechanism for failed email sends
- No way to cancel individual notifications
- No audit trail for notification attempts
- Difficult to handle partial failures
- Tight coupling between data fetching and notification delivery

## Solution Architecture

### New Entity: `subscriber_notification_message`

A new entity that represents an individual notification message to a specific subscriber.

**Entity Structure:**
```json
{
  "subscriber_email": "user@example.com",
  "notification_type": "summary",
  "date": "2024-01-01",
  "scores_data": [...],
  "status": "pending",
  "retry_count": 0,
  "max_retries": 3,
  "created_at": "2024-01-01T12:00:00Z",
  "sent_at": null,
  "cancelled_at": null,
  "error_message": null
}
```

**Workflow States:**
- `pending` → `sent` (successful send)
- `pending` → `failed` (send failure)
- `failed` → `sent` (successful retry)
- `failed` → `failed_max_retries` (max retries exceeded)
- `pending/failed` → `cancelled` (manual cancellation)

### Modified `fetch_request` Workflow

The fetch request workflow now:
1. Fetches NBA scores for the specified date range
2. Saves scores to game entities
3. Retrieves active subscribers from `subscribe_request` entities
4. Creates individual `subscriber_notification_message` entities for each subscriber
5. Each notification entity handles its own sending logic

## Implementation Details

### Files Created

#### `entity/subscriber_notification_message/__init__.py`
```python
# ABOUTME: This module contains the subscriber_notification_message entity for handling individual notification messages to subscribers.
# ABOUTME: It encapsulates the logistics of sending notifications with resend and cancellation capabilities.
```

#### `entity/subscriber_notification_message/workflow.json`
Defines three workflow transitions:
- `send_notification`: Initial attempt to send notification
- `retry_notification`: Retry failed notifications
- `cancel_notification`: Cancel pending notifications

#### `entity/subscriber_notification_message/workflow.py`
Contains the workflow processors:
- `process_send_notification()`: Handles email formatting and sending
- `process_retry_notification()`: Manages retry logic with max attempts
- `process_cancel_notification()`: Cancels notifications

### Files Modified

#### `entity/fetch_request/workflow.py`
**Key Changes:**
- Added entity service imports and initialization
- Replaced `process_notify_subscribers()` function
- Now creates notification entities instead of sending emails directly
- Retrieves subscribers from `subscribe_request` entities

**Before:**
```python
async def process_notify_subscribers(entity: dict, date_str: str, scores: List[dict]):
    subscribers_list = entity.get("subscribers", [])
    for subscriber in subscribers_list:
        # Direct email sending logic
        await send_email(...)
```

**After:**
```python
async def process_notify_subscribers(entity: dict, date_str: str, scores: List[dict]):
    # Get subscribers from subscribe_request entities
    subscribers_list = await entity_service.get_items(...)
    
    # Create notification entities for each subscriber
    for subscriber in subscribers_list:
        notification_entity = {...}
        await entity_service.add_item(
            entity_model="subscriber_notification_message",
            entity=notification_entity
        )
```

#### `entity/entities_data_design.json`
Added data structure example for the new `subscriber_notification_message` entity.

## Benefits

### 1. **Improved Reliability**
- Individual notifications can fail without affecting others
- Automatic retry mechanism with configurable max attempts
- Detailed error tracking and logging

### 2. **Better Observability**
- Complete audit trail of notification attempts
- Status tracking for each notification
- Timestamps for creation, sending, and cancellation

### 3. **Enhanced Control**
- Ability to cancel individual notifications
- Manual retry capabilities
- Configurable retry limits per notification

### 4. **Scalability**
- Notifications processed independently
- Can be distributed across multiple workers
- No blocking of the main fetch process

### 5. **Separation of Concerns**
- Data fetching logic separated from notification delivery
- Each entity has a single responsibility
- Easier to test and maintain

## Testing

The implementation was thoroughly tested with:

### Unit Tests for Notification Workflow
- ✅ Successful summary notification sending
- ✅ Successful full notification sending  
- ✅ Handling of missing required fields
- ✅ Email sending failure scenarios
- ✅ Retry logic with success
- ✅ Max retries exceeded handling
- ✅ Notification cancellation

### Integration Tests
- ✅ Fetch request creates notification entities for active subscribers
- ✅ Inactive subscribers are properly skipped
- ✅ Correct entity model and version used
- ✅ Proper subscriber retrieval from subscribe_request entities

## Usage Examples

### Creating a Notification Entity
```python
notification_entity = {
    "subscriber_email": "user@example.com",
    "notification_type": "summary",
    "date": "2024-01-01",
    "scores_data": scores,
    "status": "pending",
    "retry_count": 0,
    "max_retries": 3,
    "created_at": datetime.datetime.utcnow().isoformat()
}

notification_id = await entity_service.add_item(
    token=cyoda_auth_service,
    entity_model="subscriber_notification_message",
    entity_version=ENTITY_VERSION,
    entity=notification_entity
)
```

### Triggering a Retry
```python
# The retry is handled automatically by the workflow
# when the entity transitions to the retry_notification state
```

### Cancelling a Notification
```python
# Cancel by transitioning the entity to cancelled state
await entity_service.update_item(
    token=cyoda_auth_service,
    entity_model="subscriber_notification_message",
    entity_version=ENTITY_VERSION,
    technical_id=notification_id,
    entity={"status": "cancelled"},
    meta={"transition": "cancel_notification"}
)
```

## Future Enhancements

1. **Scheduling**: Add delayed sending capabilities
2. **Batching**: Group notifications for efficiency
3. **Templates**: Support for different email templates
4. **Preferences**: Per-subscriber delivery preferences
5. **Analytics**: Delivery success rate tracking
6. **Dead Letter Queue**: Handle permanently failed notifications

## Conclusion

The new `subscriber_notification_message` entity provides a robust, scalable solution for managing individual subscriber notifications. It offers improved reliability, better observability, and enhanced control over the notification delivery process while maintaining clean separation of concerns between data fetching and notification logistics.
