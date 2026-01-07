# Order Lifecycle

This document describes the functional requirements for the order lifecycle in our institutional trading system.

## States
- NEW
- ACK
- PARTIAL_FILL
- FILLED
- CANCELED
- REJECTED

## Transitions
- NEW -> ACK (automatic)
- ACK -> PARTIAL_FILL (automatic)
- PARTIAL_FILL -> FILLED (automatic/manual?)
- ACK -> FILLED (automatic)
- NEW -> CANCELED (manual)
- NEW -> REJECTED (manual)
- PARTIAL_FILL -> CANCELED (manual)

## Processing
Processors will handle acknowledgements, fills, and partial fills. Processors should attach the entity when interacting with calculation nodes and respect response timeouts.

## Notes
- Use synchronous processing for acknowledgements and asynchronous processing for fills and partial fills to avoid blocking the order flow.
- Include auditing information for all transitions.