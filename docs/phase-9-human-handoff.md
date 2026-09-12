# Phase 9 — Human Handoff

## Goal

Allow an AI call to safely hand a live conversation to a human destination using the existing Twilio or Plivo provider.

## Scope

- Human agent records and availability.
- Routing groups and transfer destinations.
- Deterministic routing strategies.
- Business-hours-aware routing foundation.
- Explicit AI transfer rules.
- Provider-specific transfer execution using Twilio or Plivo only.
- Transfer state and audit events.
- Safe fallback when no human is available or transfer fails.
- Tenant isolation and authorization.
- Tests for routing, state transitions, and provider selection.

## State flow

`AI_ACTIVE → HANDOFF_REQUESTED → TRANSFERRING → HUMAN_CONNECTED`

Failure paths:

`TRANSFERRING → AI_ACTIVE` when the transfer fails and the call remains connected.

`TRANSFERRING → HANDOFF_FAILED → COMPLETED` when the call cannot remain active.

A provider terminal callback remains authoritative for final call completion.

## Provider policy

Only Twilio and Plivo are supported. Provider selection comes from the call's configured phone number; no third provider is introduced.

## Production gate

Phase 9 is not complete until backend tests, frontend build, CI, and provider-specific transfer E2E validation pass.
