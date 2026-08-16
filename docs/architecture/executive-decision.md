# TX AI Lab - Executive Architecture Decision

## Decision

TX AI Lab will evolve from Athkachatbots into a reusable AI platform while keeping Athkachatbots as Product #1.

The system will remain:

- One repository
- One backend deployment
- Modular Monolith
- API-first
- Multi-tenant

## Platform Domains

The platform is divided logically into:

- Knowledge Platform
- Agent Runtime Platform
- Evaluation Platform
- Shared Platform Services
- Products / Athkachatbots

## Why

The current system already contains reusable knowledge, AI runtime, tenancy, and evaluation capabilities.

A rewrite or early microservice split would add complexity without solving the current architectural problem.

The current problem is ownership and boundaries, not deployment topology.

## Migration Principle

We will:

1. Define ownership.
2. Stabilize contracts.
3. Protect boundaries with tests.
4. Refactor gradually.
5. Move code only when useful.

We will NOT perform a full rewrite.

## Future Service Extraction

A module may become a separate service later only when justified by measured needs such as:

- Independent scaling
- Independent deployment
- Security isolation
- Reliability requirements
- Team ownership
- Performance bottlenecks
