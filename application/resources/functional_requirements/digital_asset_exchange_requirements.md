# Digital Asset Exchange — Functional Requirements

## Overview and goals
Build a production-grade digital asset exchange that supports real-time market data ingestion, a performant order matching engine, secure wallet management, KYC/AML compliance, enterprise-grade security, and comprehensive trading analytics.

## Functional Requirements
- Real-time price feeds: ingest streaming ticks, normalize data, persist snapshots, broadcast updates
- Order matching: support limit/market/IOC/FOK/iceberg, price-time priority, partial fills, order book persistence and replay
- Wallet management: hot/cold wallets, deposit/withdrawal flows, ledger with double-entry accounting
- KYC/AML: onboarding, document verification, sanctions screening, case management
- Trading analytics: real-time metrics, historical reports, dashboards

## Mapping to Entities & Workflows
- Users, Wallets, Orders, Trades, KYCRecords, LedgerEntries, MarketData entities
- Workflows: PriceFeedIngestion, OrderMatching, DepositProcessing, WithdrawalProcessing, KYCOnboarding, AMLMonitoring

## Non-Functional Requirements
- High availability and horizontal scalability
- Observability: tracing, metrics, structured logs
- Security: RBAC, encryption, secure secrets management
- Compliance: audit logs, exportable reports
- Testability: unit, integration, load testing harness

## Acceptance Criteria
- End-to-end demo: ingest market data → place orders → produce trades → ledger updated
- KYC flow: verified user can trade; unverified flagged
- AML flow: suspicious transactions generate alerts/cases
- Performance: matching engine handles target TPS in acceptance tests

