# 02-domain-model: Business Domain Model

## Purpose

This document defines the business domain of the Modern AI Agent Platform. It establishes the core entities, their relationships, lifecycle, and business rules that govern the platform. This document focuses exclusively on the business domain—what exists, how entities relate, and what rules apply. It contains no implementation details, database schemas, API specifications, or architectural decisions.

This document defines the ubiquitous language used across all project documentation, specifications, and code.

## Core Domain

**Multi-Tenant SaaS Platform for AI Agents**

The Modern AI Agent Platform is a business that provides infrastructure for companies (Tenants) to deploy AI-powered chatbots (AI Agents) without building AI systems themselves. Each Tenant operates in complete isolation, managing multiple AI Agents, each with its own Knowledge Base, Conversations, and business role configuration.

## Core Entities

### Platform

**Purpose**: The Modern AI Agent Platform system as a whole.

**Responsibility**: Provides multi-tenant SaaS infrastructure, enforces tenant isolation, manages system-wide operations, and maintains platform health.

**Relationships**:
- Contains multiple Tenants
- Managed by Platform Administrators

**Lifecycle**: The Platform exists as long as the SaaS service operates. It is not created or destroyed through normal business operations.

---

### Platform Administrator

**Purpose**: A person or system entity with authority to manage the entire platform.

**Responsibility**: Monitors system health, oversees tenant operations, manages platform-wide configuration, and ensures platform availability.

**Relationships**:
- Manages the Platform
- Has visibility across all Tenants (for operational purposes only)
- Cannot access Tenant business data without proper authorization

**Lifecycle**: Created when granted platform administrative access. Deactivated when administrative privileges are revoked.

---

### Tenant

**Purpose**: An organization (company) that uses the platform to deploy AI chatbots.

**Responsibility**: Owns and manages AI Agents, Knowledge Bases, Conversations, and configurations. Operates in complete isolation from other Tenants.

**Relationships**:
- Belongs to the Platform
- Owns one or more AI Agents
- Has one or more Tenant Users
- All owned entities (Agents, Knowledge, Conversations) are isolated from other Tenants

**Lifecycle**:
- Created when a company subscribes to the platform
- Active while subscription is valid
- Suspended or deactivated upon subscription termination
- May be permanently deleted following data retention policies

---

### Tenant User

**Purpose**: A person who works for a Tenant organization and uses the platform to configure agents and manage knowledge.

**Responsibility**: Configures AI Agents, manages Knowledge Bases, uploads Knowledge Documents, defines Agent Instructions, and monitors Conversations.

**Relationships**:
- Belongs to exactly one Tenant
- Can manage multiple AI Agents within their Tenant
- Can access Knowledge Bases and Conversations for Agents they have permission to manage

**Lifecycle**:
- Created when invited to a Tenant organization
- Active while employed or authorized by the Tenant
- Deactivated when access is revoked or employment ends
- May be permanently deleted following data retention policies

---

### AI Agent

**Purpose**: An AI-powered chatbot deployed by a Tenant for a specific business role (customer support, sales, HR, product information, etc.).

**Responsibility**: Interacts with Website Visitors through Conversations, retrieves information from its Knowledge Base, follows its Agent Instructions, and provides responses within its defined scope.

**Relationships**:
- Belongs to exactly one Tenant
- Owns exactly one Knowledge Base
- Has zero or more Conversations
- Has exactly one Chat Widget configuration
- Has exactly one set of Agent Instructions
- Uses one System Prompt

**Lifecycle**:
- Created by a Tenant User
- Configured with knowledge, instructions, and widget settings
- Deployed when ready to interact with visitors
- Active while serving conversations
- Can be paused or deactivated
- May be permanently deleted, removing all associated data (Knowledge Base, Conversations, Messages)

---

### Knowledge Base

**Purpose**: A collection of business knowledge owned by an AI Agent, used to answer questions within the Agent's scope.

**Responsibility**: Stores Knowledge Documents, organizes Knowledge Chunks, maintains Embeddings for semantic search, and provides context for the AI Agent's responses.

**Relationships**:
- Belongs to exactly one AI Agent
- Contains zero or more Knowledge Documents
- Organized into Knowledge Chunks
- Each chunk has one or more Embeddings

**Lifecycle**:
- Created automatically when an AI Agent is created
- Grows as Knowledge Documents are uploaded
- Updated when documents are added, modified, or removed
- Deleted when the owning AI Agent is deleted

---

### Knowledge Document

**Purpose**: A single piece of business content (text file, PDF, web page, FAQ, policy document, etc.) uploaded to a Knowledge Base.

**Responsibility**: Represents original source content that an AI Agent uses to answer questions.

**Relationships**:
- Belongs to exactly one Knowledge Base
- Divided into one or more Knowledge Chunks for processing
- Maintains metadata (filename, upload date, content type, source URL)

**Lifecycle**:
- Created when uploaded by a Tenant User
- Processed into Knowledge Chunks
- Can be updated or replaced
- Deleted when removed by a Tenant User or when the Knowledge Base is deleted

---

### Knowledge Chunk

**Purpose**: A segment of a Knowledge Document, optimized for semantic search and retrieval.

**Responsibility**: Represents a portion of original content with appropriate size and context for embedding generation and retrieval.

**Relationships**:
- Belongs to exactly one Knowledge Document
- Has one or more Embeddings (depending on embedding strategy)
- Returned as a Search Result during knowledge retrieval

**Lifecycle**:
- Created when a Knowledge Document is processed
- Generated based on content structure (paragraphs, sections, sentences)
- Maintains reference to source document
- Deleted when the source Knowledge Document is deleted

---

### Embedding

**Purpose**: A numerical vector representation of a Knowledge Chunk, enabling semantic similarity search.

**Responsibility**: Enables the RAG Pipeline to find relevant knowledge based on semantic meaning rather than exact keyword matching.

**Relationships**:
- Belongs to exactly one Knowledge Chunk
- Used by the RAG Pipeline during Search Result generation
- Generated by an embedding model (OpenAI, Cohere, etc.)

**Lifecycle**:
- Created when a Knowledge Chunk is processed
- Stored for efficient similarity search
- Regenerated if embedding model or strategy changes
- Deleted when the associated Knowledge Chunk is deleted

---

### Conversation

**Purpose**: A dialog session between a Website Visitor and an AI Agent.

**Responsibility**: Tracks the interaction history, maintains context, and stores all Messages exchanged during the session.

**Relationships**:
- Belongs to exactly one AI Agent
- Contains one or more Messages
- May be associated with a visitor identifier (for continuity across sessions)

**Lifecycle**:
- Created when a Website Visitor initiates interaction with a Chat Widget
- Active while the visitor is engaged
- Persists after the visitor leaves (for analysis and history)
- May be archived or deleted following data retention policies

---

### Message

**Purpose**: A single turn in a Conversation—either a question from a Website Visitor or a response from an AI Agent.

**Responsibility**: Records the exact content, timestamp, role (user or agent), and any associated metadata (retrieved knowledge, confidence scores, etc.).

**Relationships**:
- Belongs to exactly one Conversation
- Linked to the AI Agent that generated it (for agent messages)
- May reference Search Results that informed the response

**Lifecycle**:
- Created when a visitor sends a message or when an agent responds
- Immutable once created
- Persists for conversation history and analytics
- Deleted when the parent Conversation is deleted

---

### Chat Widget

**Purpose**: The embedded user interface configuration that Website Visitors use to interact with an AI Agent.

**Responsibility**: Defines appearance, behavior, branding, and interaction settings for the chatbot interface embedded on the Tenant's website.

**Relationships**:
- Belongs to exactly one AI Agent
- Used by Website Visitors to initiate Conversations
- References the Agent's instructions and knowledge

**Lifecycle**:
- Created when an AI Agent is deployed
- Configured with branding, colors, welcome message, and behavior settings
- Updated as Tenant User customizes the widget
- Deleted when the AI Agent is deleted

---

### System Prompt

**Purpose**: The foundational instruction template provided to the large language model that powers an AI Agent.

**Responsibility**: Defines the agent's persona, tone, general behavior, and interaction guidelines at the platform level.

**Relationships**:
- Used by one or more AI Agents
- Combined with Agent Instructions to form the complete prompt
- Maintained at the platform level (not customizable per Tenant)

**Lifecycle**:
- Created by platform developers
- Updated as platform capabilities evolve
- Versioned for consistency and rollback

---

### Agent Instructions

**Purpose**: Tenant-specific and Agent-specific directives that customize how an AI Agent behaves.

**Responsibility**: Defines the Agent's business role, scope, tone, response style, and any special rules the Tenant requires.

**Relationships**:
- Belongs to exactly one AI Agent
- Combined with System Prompt to form the complete instruction set
- Customized by Tenant Users

**Lifecycle**:
- Created when an AI Agent is configured
- Updated as Tenant Users refine the Agent's behavior
- Deleted when the AI Agent is deleted

---

### Search Result

**Purpose**: A Knowledge Chunk retrieved by the RAG Pipeline as relevant to a visitor's question.

**Responsibility**: Provides context to the AI Agent for generating an informed response based on the Knowledge Base.

**Relationships**:
- Derived from one or more Knowledge Chunks
- Used temporarily during message generation
- May be logged as part of a Message for traceability

**Lifecycle**:
- Created during the RAG Pipeline execution
- Exists only for the duration of a single message generation
- May be persisted for analytics or explainability

---

### RAG Pipeline

**Purpose**: The Retrieval-Augmented Generation process that retrieves relevant knowledge and generates responses.

**Responsibility**: Executes semantic search against the Knowledge Base, ranks Search Results, injects context into the AI Agent's prompt, and generates responses using the large language model.

**Relationships**:
- Operates on a single AI Agent's Knowledge Base
- Retrieves Search Results from Knowledge Chunks and Embeddings
- Produces Messages in response to visitor input
- Scoped strictly by Tenant and Agent boundaries

**Lifecycle**:
- Invoked each time a Website Visitor sends a message
- Executes retrieval, ranking, context injection, and generation
- Completes when a Message is produced

---

## Relationships

### Hierarchical Structure

```
Platform
  └─ Tenant
       ├─ Tenant User
       └─ AI Agent
            ├─ Knowledge Base
            │    └─ Knowledge Document
            │         └─ Knowledge Chunk
            │              └─ Embedding
            ├─ Conversation
            │    └─ Message
            ├─ Chat Widget
            └─ Agent Instructions
```

### Key Relationships

- **Platform contains Tenants**: The platform is a multi-tenant system. Each Tenant operates independently.
- **Tenant owns AI Agents**: A Tenant can create and manage multiple AI Agents. Each Agent belongs to exactly one Tenant.
- **AI Agent owns Knowledge Base**: Each AI Agent has exactly one Knowledge Base. Knowledge is never shared across Agents or Tenants.
- **Knowledge Base contains Documents**: A Knowledge Base organizes multiple Knowledge Documents.
- **Knowledge Document is divided into Chunks**: Documents are segmented into smaller chunks for efficient retrieval.
- **Knowledge Chunk has Embeddings**: Each chunk is converted into vector embeddings for semantic search.
- **AI Agent has Conversations**: An Agent can have many ongoing or historical Conversations.
- **Conversation contains Messages**: Each Conversation is composed of a sequence of Messages.
- **AI Agent has one Chat Widget**: The widget configuration is specific to each Agent.
- **AI Agent has one set of Agent Instructions**: Instructions define the Agent's specific behavior and scope.
- **RAG Pipeline retrieves from Knowledge Base**: The pipeline enforces strict isolation, retrieving only from the Agent's own Knowledge Base.

---

## Ownership Rules

Ownership in the Modern AI Agent Platform follows strict hierarchical rules:

- **Platform owns Tenants**: All Tenants exist within and are owned by the Platform.
- **Tenant owns AI Agents**: Each AI Agent is owned by exactly one Tenant.
- **Tenant owns Tenant Users**: Each Tenant User belongs to exactly one Tenant.
- **AI Agent owns Knowledge Base**: Each Knowledge Base is owned by exactly one AI Agent.
- **AI Agent owns Conversations**: Each Conversation is owned by exactly one AI Agent.
- **AI Agent owns Chat Widget**: Each Chat Widget is owned by exactly one AI Agent.
- **AI Agent owns Agent Instructions**: Each set of Agent Instructions is owned by exactly one AI Agent.
- **Knowledge Base owns Documents**: Each Knowledge Document is owned by exactly one Knowledge Base.
- **Knowledge Document owns Chunks**: Each Knowledge Chunk is owned by exactly one Knowledge Document.
- **Knowledge Chunk owns Embeddings**: Each Embedding is owned by exactly one Knowledge Chunk.
- **Conversation owns Messages**: Each Message is owned by exactly one Conversation.

**Ownership is exclusive**: An entity can have only one owner. Shared ownership is not allowed.

**Ownership is cascading**: When an owner is deleted, all owned entities are also deleted.

---

## Business Rules

### Tenant Isolation Rules

- Every AI Agent belongs to exactly one Tenant.
- Tenant A cannot access, view, or modify Tenant B's Agents, Knowledge Bases, Conversations, or configurations.
- Knowledge retrieval must always be scoped by Tenant and Agent—cross-Tenant knowledge access is prohibited.
- Search Results are derived only from the requesting Agent's Knowledge Base.
- Platform Administrators can monitor system health but cannot access Tenant business data without explicit authorization.

### Agent Isolation Rules

- Each AI Agent has its own isolated Knowledge Base.
- Agent A cannot retrieve knowledge from Agent B's Knowledge Base, even if both belong to the same Tenant.
- Conversations belong to exactly one Agent and cannot be transferred or shared across Agents.
- Messages reference only the Knowledge Base of the Agent that generated them.

### Knowledge Management Rules

- A Knowledge Document belongs to exactly one Knowledge Base.
- A Knowledge Chunk belongs to exactly one Knowledge Document.
- An Embedding belongs to exactly one Knowledge Chunk.
- When a Knowledge Document is deleted, all associated Chunks and Embeddings are deleted.
- When an AI Agent is deleted, its Knowledge Base, all Documents, Chunks, Embeddings, Conversations, and Messages are deleted.

### Conversation Rules

- A Conversation belongs to exactly one AI Agent.
- A Message belongs to exactly one Conversation.
- Messages are immutable once created.
- A Conversation cannot be transferred between Agents.

### Agent Behavior Rules

- An AI Agent answers questions only within its assigned business role and available Knowledge Base.
- If the Agent's Knowledge Base does not contain relevant information, the Agent returns a short out-of-scope response.
- The Agent does not generate unsupported information or speculate beyond its knowledge.
- Agent Instructions define scope, but the System Prompt enforces platform-level behavior constraints.

### Data Lifecycle Rules

- When a Tenant is deleted, all owned Agents, Knowledge Bases, Conversations, and configurations are deleted.
- When an AI Agent is deleted, all associated data (Knowledge Base, Conversations, Messages, Chat Widget, Agent Instructions) is deleted.
- When a Knowledge Document is deleted, all derived Chunks and Embeddings are deleted.

### Access Control Rules

- Tenant Users can only manage Agents, Knowledge Bases, and Conversations within their own Tenant.
- Website Visitors interact only with the specific AI Agent associated with the embedded Chat Widget.
- Platform Administrators have operational access but cannot modify Tenant business logic or configurations without authorization.

---

## Ubiquitous Language

**Platform**: The Modern AI Agent Platform—a multi-tenant SaaS system for deploying AI chatbots.

**Platform Administrator**: A person or system with authority to manage the entire platform.

**Tenant**: An organization (company) that subscribes to the platform to deploy AI chatbots.

**Tenant User**: A person employed or authorized by a Tenant to configure agents and manage knowledge.

**AI Agent**: An AI-powered chatbot deployed by a Tenant for a specific business role.

**Knowledge Base**: A collection of business knowledge owned by an AI Agent, used to answer questions.

**Knowledge Document**: A single piece of content (file, web page, policy, FAQ) uploaded to a Knowledge Base.

**Knowledge Chunk**: A segment of a Knowledge Document, optimized for semantic search and retrieval.

**Embedding**: A numerical vector representation of a Knowledge Chunk, enabling semantic similarity search.

**Conversation**: A dialog session between a Website Visitor and an AI Agent.

**Message**: A single turn in a Conversation—a question from a visitor or a response from an agent.

**Chat Widget**: The embedded user interface configuration that Website Visitors use to interact with an AI Agent.

**System Prompt**: The foundational instruction template provided to the large language model, maintained at the platform level.

**Agent Instructions**: Tenant-specific and Agent-specific directives that customize how an AI Agent behaves.

**Website Visitor**: An end user who interacts with an AI Agent through a Chat Widget embedded on a Tenant's website.

**Search Result**: A Knowledge Chunk retrieved by the RAG Pipeline as relevant to a visitor's question.

**RAG Pipeline**: The Retrieval-Augmented Generation process that retrieves relevant knowledge and generates responses.

**Tenant Isolation**: The principle that Tenant data, agents, and knowledge are completely separated and inaccessible across Tenants.

**Agent Isolation**: The principle that each AI Agent operates with its own isolated Knowledge Base and cannot access other Agents' knowledge.

**Out-of-Scope Response**: A short response returned by an AI Agent when its Knowledge Base does not contain relevant information to answer a question.

**Semantic Search**: The process of finding Knowledge Chunks based on meaning similarity rather than exact keyword matching.

**Retrieval**: The process of finding relevant Knowledge Chunks from a Knowledge Base using semantic search.

**Context Injection**: The process of including retrieved Search Results in the AI Agent's prompt to inform response generation.

**Business Role**: The specific function an AI Agent is configured to perform (e.g., customer support, sales, HR, product information).

---

## Non-Negotiable Domain Principles

The following principles apply to every design, specification, and implementation in this project:

1. **The platform remains generic**: No customer-specific logic, no hardcoded behaviors for specific industries or companies.

2. **No shared tenant knowledge**: Knowledge Bases are owned by a single AI Agent and are never shared across Agents or Tenants.

3. **No cross-tenant access**: Tenant A cannot access, view, or modify Tenant B's data, configurations, or operations.

4. **Agents answer only within their assigned responsibility**: An AI Agent responds only based on its Knowledge Base and Agent Instructions. If knowledge is insufficient, the agent returns an out-of-scope response.

5. **Knowledge retrieval is always scoped**: The RAG Pipeline enforces strict boundaries—retrieval is scoped by Tenant and Agent. Cross-Tenant or cross-Agent retrieval is prohibited.

6. **Tenant isolation is mandatory**: Every entity (Agent, Knowledge Base, Conversation, Message) is owned by a Tenant and isolated from other Tenants.

7. **Agent isolation is mandatory**: Each AI Agent operates independently with its own Knowledge Base, Conversations, and configurations. Agents cannot share or access each other's knowledge.

8. **If knowledge is insufficient, return an out-of-scope response**: An AI Agent does not speculate, invent information, or generate unsupported answers. If the Knowledge Base lacks relevant content, the agent responds with a short out-of-scope message.

---

## References

- Project context and current phase: #[[file:01-project.md]]

---

## Domain Boundaries

This document defines business concepts only. It establishes the language and rules of the business domain.

**This document must never contain:**

- **Database schema**: Table definitions, column types, indexes, foreign keys, or query structures belong in architecture or implementation documents.
- **API endpoints**: REST paths, HTTP methods, request/response formats, or API contracts belong in API specifications.
- **Frameworks**: Specific technologies (FastAPI, Django, Flask, Express, etc.) belong in architecture documents.
- **Programming languages**: Language choices (Python, TypeScript, JavaScript, etc.) belong in architecture documents.
- **Deployment**: Infrastructure, hosting, containers, orchestration, or scaling strategies belong in deployment documents.
- **Infrastructure**: Servers, databases, caches, message queues, or cloud services belong in infrastructure documents.
- **Implementation details**: Code structure, file organization, module design, or algorithm choices belong in implementation specifications.

This document focuses exclusively on **what exists** (entities), **how entities relate** (relationships), **what rules govern behavior** (business rules), and **what terms mean** (ubiquitous language).

When implementation questions arise, refer to:
- Architecture: #[[file:03-system-architecture.md]]
- Coding standards: #[[file:04-coding-standards.md]]
