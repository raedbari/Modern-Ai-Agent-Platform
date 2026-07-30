# 06-ai-platform: AI Platform Patterns and Integration

## Purpose

This document defines patterns and practices for integrating AI capabilities into the Modern AI Agent Platform. It establishes how AI Agents are structured, how the RAG (Retrieval-Augmented Generation) pipeline operates, how knowledge is managed and retrieved, how prompts are constructed, how embeddings are generated, and how AI providers are integrated. This document focuses on AI-specific architectural patterns, not general system architecture or business domain definitions.

## AI Agent Architecture

### Agent Lifecycle

AI Agents in the Modern AI Agent Platform follow a defined lifecycle:

**Creation**: A Tenant User creates an agent with a name, business role, and initial instructions. The agent is assigned a unique identifier and associated with the tenant. A Knowledge Base is created automatically.

**Configuration**: The agent's instructions, model selection, temperature, and other parameters are configured. The Chat Widget appearance and behavior are customized.

**Knowledge Loading**: Knowledge Documents are uploaded to the agent's Knowledge Base. Documents are processed into chunks and embeddings.

**Deployment**: The agent is marked as active and ready to serve conversations. The Chat Widget can be embedded on the tenant's website.

**Operation**: The agent receives messages from Website Visitors, retrieves relevant knowledge, and generates responses using the RAG pipeline.

**Maintenance**: The agent's instructions and knowledge are updated as needed. Performance is monitored and adjustments are made.

**Deactivation**: The agent is paused or deleted when no longer needed. All associated data is cleaned up.

### Agent Components

Each AI Agent is composed of:

**Knowledge Base**: The agent's isolated collection of business knowledge. Contains Knowledge Documents, Chunks, and Embeddings. Used exclusively by this agent—never shared across agents or tenants.

**Agent Instructions**: Tenant-specific and agent-specific directives that define the agent's behavior, tone, scope, and response style. Combined with the System Prompt to form the complete instruction set.

**System Prompt**: Platform-level foundational instructions provided to the language model. Defines the agent's persona, general behavior, and interaction guidelines. Maintained at the platform level.

**Chat Widget**: The embeddable user interface configuration that Website Visitors use to interact with the agent. Defines appearance, branding, and behavior.

**Conversation History**: The record of all interactions the agent has had with Website Visitors. Used for context and continuity.

### Agent Isolation

Each AI Agent operates independently with strict isolation:

- **Knowledge Isolation**: Each agent has its own Knowledge Base. Knowledge retrieval is scoped to the agent's knowledge only.
- **Conversation Isolation**: Conversations belong to a specific agent and are not shared across agents.
- **Configuration Isolation**: Agent Instructions and Chat Widget configurations are specific to each agent.

Agent isolation is enforced at every layer. The RAG pipeline always filters by tenant ID and agent ID. No cross-agent knowledge access is permitted.

See #[[file:02-domain-model.md]] for detailed entity definitions and relationships.

## RAG (Retrieval-Augmented Generation) Pipeline

The RAG pipeline is the core mechanism that enables AI Agents to answer questions based on their Knowledge Base. It combines semantic search (retrieval) with language model inference (generation).

### Pipeline Stages

**1. Query Processing**:
- Receive user message from Website Visitor
- Extract the question or intent
- Generate query embedding using the embedding model

**2. Knowledge Retrieval**:
- Search the agent's Knowledge Base using semantic similarity
- Scope search by tenant ID and agent ID (mandatory)
- Rank results by relevance score
- Select top N most relevant Knowledge Chunks (typically 3-5)

**3. Context Construction**:
- Combine retrieved Knowledge Chunks into context
- Format context for injection into the prompt
- Maintain chunk source references for traceability

**4. Prompt Assembly**:
- Combine System Prompt, Agent Instructions, context, conversation history, and user message
- Structure prompt according to the language model's expected format
- Ensure token limits are respected

**5. Response Generation**:
- Send prompt to the language model
- Receive generated response
- Validate response quality and relevance

**6. Response Delivery**:
- Return response to Website Visitor
- Store message in Conversation history
- Log retrieval and generation metadata for monitoring

### Retrieval Scoping Rules

**Mandatory Scoping**:
- Every retrieval operation MUST filter by tenant ID
- Every retrieval operation MUST filter by agent ID
- No cross-tenant retrieval is allowed
- No cross-agent retrieval is allowed

**Validation**:
- Verify tenant context is established before retrieval
- Verify agent context is established before retrieval
- Reject operations missing tenant or agent context
- Log all retrieval operations with tenant and agent identifiers

**Example Query Structure**:
```python
# CORRECT: Properly scoped retrieval
def retrieve_knowledge(
    tenant_id: str,
    agent_id: str,
    query_embedding: List[float],
    limit: int = 5
) -> List[KnowledgeChunk]:
    return knowledge_repository.search(
        tenant_id=tenant_id,      # Mandatory
        agent_id=agent_id,        # Mandatory
        embedding=query_embedding,
        limit=limit
    )
```

### Out-of-Scope Behavior

When the agent's Knowledge Base does not contain relevant information to answer a question:

**Do NOT**:
- Generate unsupported information or speculate
- Invent facts not present in the Knowledge Base
- Answer beyond the agent's assigned business role
- Use general knowledge outside the Knowledge Base

**DO**:
- Return a short, clear out-of-scope response
- Indicate that the question is outside the agent's knowledge area
- Suggest alternative resources if configured
- Maintain professional tone

**Example Out-of-Scope Response**:
> "I don't have information about that in my knowledge base. Please contact our support team for assistance."

## Prompt Management

### Prompt Structure

Prompts for AI Agents follow a structured format:

**1. System Prompt** (platform-level):
- Defines the agent's foundational persona and behavior
- Establishes platform-wide interaction guidelines
- Sets tone, safety constraints, and operational boundaries
- Maintained by platform developers, not customizable by tenants

**2. Agent Instructions** (tenant-specific):
- Defines the agent's business role and scope
- Specifies response style, tone, and constraints
- Provides role-specific guidance (e.g., "You are a customer support agent for Acme Corp")
- Customized by Tenant Users for each agent

**3. Context** (retrieved knowledge):
- Relevant Knowledge Chunks retrieved from the agent's Knowledge Base
- Formatted as context to inform the response
- Scoped strictly by tenant and agent boundaries

**4. Conversation History** (recent messages):
- Recent messages from the current conversation
- Provides continuity and context for multi-turn interactions
- Limited to recent history to manage token usage

**5. User Message** (current input):
- The Website Visitor's current question or message
- The input the agent is responding to

### Prompt Construction Pattern

```
[System Prompt]
Platform-level instructions and persona definition.

[Agent Instructions]
Tenant-specific business role and behavior customization.

[Context]
Relevant knowledge retrieved from Knowledge Base:
- Chunk 1: [content]
- Chunk 2: [content]
- Chunk 3: [content]

[Conversation History]
User: [previous message]
Agent: [previous response]

[User Message]
User: [current message]
```

### Prompt Best Practices

- **Keep System Prompt stable**: Changes affect all agents. Update carefully and version appropriately.
- **Keep Agent Instructions clear and specific**: Vague instructions lead to inconsistent behavior.
- **Limit context size**: Retrieve only the most relevant chunks. More context is not always better.
- **Respect token limits**: Monitor token usage and truncate when necessary.
- **Test prompts thoroughly**: Validate behavior with diverse inputs before deploying.

## Embedding Generation

Embeddings are numerical vector representations of text that enable semantic similarity search. The platform uses embeddings to retrieve relevant knowledge from the Knowledge Base.

### Embedding Workflow

**1. Document Upload**:
- Tenant User uploads a Knowledge Document
- Document is parsed and text content is extracted

**2. Chunking**:
- Document text is divided into Knowledge Chunks
- Chunk size is optimized for embedding model limits (typically 512 tokens)
- Chunks overlap slightly to maintain context continuity

**3. Embedding Generation**:
- Each Knowledge Chunk is sent to the embedding model
- Embedding model returns a vector representation (e.g., 1536 dimensions for OpenAI text-embedding-3-small)
- Embeddings are stored with references to the source chunk

**4. Storage**:
- Embeddings are stored in a vector database or database with vector support
- Indexed for efficient similarity search
- Tagged with tenant ID and agent ID for scoping

### Embedding Best Practices

- **Use consistent embedding models**: Switching models requires re-embedding all knowledge.
- **Optimize chunk size**: Balance between context completeness and model limits.
- **Batch embedding generation**: Reduce API calls by batching chunks when possible.
- **Monitor embedding costs**: Embedding generation incurs API costs. Track usage.
- **Handle embedding failures gracefully**: Retry transient errors, log permanent failures.

### Semantic Search

Semantic search finds Knowledge Chunks based on meaning similarity rather than exact keyword matching.

**Search Process**:
1. Generate embedding for the user's query
2. Compare query embedding to stored Knowledge Chunk embeddings
3. Calculate similarity scores (cosine similarity or distance)
4. Rank chunks by similarity score
5. Return top N most relevant chunks

**Similarity Metrics**:
- **Cosine Similarity**: Measures angle between vectors (range: -1 to 1, higher is more similar)
- **Euclidean Distance**: Measures distance between vectors (lower is more similar)
- **Dot Product**: Measures alignment between vectors (higher is more similar)

**Scoping**:
- Search is always scoped by tenant ID and agent ID
- No cross-tenant or cross-agent search is allowed
- Results are filtered before ranking to enforce isolation

## AI Provider Integration

The platform integrates with external AI providers for language model inference and embedding generation. Providers are abstracted to allow flexibility and provider changes.

### Provider Abstraction

**AIClient Interface**:
- Abstracts provider-specific details
- Supports multiple providers (OpenAI, Anthropic, Cohere, etc.)
- Provides consistent interface for generation and embedding

**Benefits**:
- Switch providers without changing application logic
- Support multiple providers simultaneously
- Implement fallback and failover strategies
- Isolate provider-specific code

### Provider Selection

Providers are selected based on:
- Agent configuration (model preference)
- Tenant configuration (if tenant-specific providers are supported)
- Platform configuration (default provider)
- Availability and fallback rules

### Rate Limiting and Cost Management

AI provider integration must handle:

**Rate Limiting**:
- Respect provider rate limits
- Implement retry with exponential backoff
- Queue requests when limits are approached
- Monitor usage against quotas

**Cost Management**:
- Track token usage per request
- Monitor total costs per tenant and agent
- Implement usage limits if necessary
- Optimize token usage (prompt size, context length)

**Error Handling**:
- Handle transient errors (timeouts, rate limits) with retries
- Handle permanent errors (invalid API key, quota exceeded) with clear messages
- Log errors with context (tenant, agent, operation)
- Provide fallback responses when generation fails

### Provider Configuration

AI providers are configured using environment variables with the MAAP_ prefix:

```bash
MAAP_AI_PROVIDER=openai
MAAP_AI_API_KEY=sk-...
MAAP_EMBEDDING_MODEL=text-embedding-3-small
MAAP_GENERATION_MODEL=gpt-4
MAAP_AI_TIMEOUT=30
MAAP_AI_MAX_RETRIES=3
```

See #[[file:07-security.md]] for secret management best practices.

## Knowledge Management Patterns

### Document Processing Pipeline

**1. Upload**:
- Validate file type and size
- Scan for security issues (if applicable)
- Store original document in file storage

**2. Text Extraction**:
- Extract text content from document (PDF, DOCX, TXT, HTML)
- Preserve structure and formatting where relevant
- Handle extraction errors gracefully

**3. Chunking**:
- Divide text into manageable chunks
- Respect sentence and paragraph boundaries
- Maintain chunk size within embedding model limits
- Overlap chunks to preserve context continuity

**4. Embedding Generation**:
- Generate embeddings for each chunk
- Batch requests to embedding provider
- Store embeddings with chunk references

**5. Indexing**:
- Store chunks and embeddings in database
- Index by tenant ID and agent ID
- Enable efficient similarity search

**6. Validation**:
- Verify all chunks have embeddings
- Confirm document is searchable
- Mark document as processed and ready

### Chunking Strategies

**Fixed-Size Chunking**:
- Divide text into chunks of fixed token count
- Simple and predictable
- May break sentences or paragraphs

**Sentence-Based Chunking**:
- Chunk by complete sentences
- More natural boundaries
- Variable chunk sizes

**Paragraph-Based Chunking**:
- Chunk by paragraphs or sections
- Preserves semantic coherence
- May exceed token limits for large paragraphs

**Hybrid Chunking**:
- Combine strategies based on document structure
- Optimize for coherence and size constraints

### Knowledge Update Patterns

**Adding Knowledge**:
- Upload new documents
- Process and embed automatically
- Immediately available for retrieval

**Updating Knowledge**:
- Replace existing document
- Reprocess and re-embed
- Update or invalidate old embeddings

**Deleting Knowledge**:
- Remove document
- Delete associated chunks and embeddings
- Update indexes

## Conversation Management

### Conversation Context

Conversations maintain context across multiple message exchanges:

**Context Window**:
- Recent messages from the current conversation
- Limited to recent history (e.g., last 5-10 messages)
- Manages token usage while maintaining continuity

**Context Injection**:
- Include conversation history in prompt
- Format as alternating user/agent messages
- Truncate if exceeds token limits

### Conversation State

Conversations may track:
- Conversation ID (unique identifier)
- Agent ID (which agent is serving the conversation)
- Visitor identifier (for continuity across sessions)
- Message history
- Metadata (start time, message count, etc.)

### Multi-Turn Interactions

The RAG pipeline supports multi-turn conversations:
- Each message generation includes conversation history
- Context from previous turns informs current response
- Knowledge retrieval considers conversation context

## AI-Specific Testing Patterns

### Testing AI Agent Behavior

**Mock LLM Responses**:
- Mock language model API responses for predictable testing
- Test prompt construction without incurring API costs
- Verify error handling and retry logic

**Test Knowledge Retrieval**:
- Test semantic search with known queries and expected results
- Verify tenant and agent isolation in retrieval
- Test ranking and filtering logic

**Test Prompt Assembly**:
- Verify prompts include all required components
- Test token limit handling
- Validate prompt structure

**Test Out-of-Scope Behavior**:
- Test responses when knowledge is insufficient
- Verify agents do not generate unsupported information
- Validate out-of-scope response messages

### Testing Embedding Generation

- Test chunking strategies with various document types
- Verify embeddings are generated and stored correctly
- Test embedding provider integration and error handling
- Validate semantic search accuracy

See #[[file:08-testing.md]] for comprehensive testing strategies.

## Performance Considerations

### Latency Optimization

**Retrieval Latency**:
- Optimize semantic search queries
- Use appropriate indexing strategies
- Cache frequently accessed embeddings

**Generation Latency**:
- Minimize prompt size when possible
- Monitor language model response times
- Implement timeouts and fallbacks

**End-to-End Latency**:
- Profile the entire RAG pipeline
- Identify and optimize bottlenecks
- Monitor and alert on latency spikes

### Caching Strategies

**Embedding Cache**:
- Cache embeddings to avoid re-generation
- Invalidate cache when documents are updated
- Scope cache keys by tenant and agent

**Response Cache**:
- Cache responses for frequently asked questions (if appropriate)
- Short TTL to ensure freshness
- Scope cache keys by tenant and agent

**Knowledge Cache**:
- Cache frequently retrieved Knowledge Chunks
- Invalidate cache when knowledge is updated

## AI Safety and Quality

### Response Validation

- Validate that responses are relevant to the question
- Detect and filter inappropriate or harmful content
- Monitor response quality metrics

### Hallucination Detection

- Compare generated responses to retrieved knowledge
- Flag responses that introduce unsupported information
- Log and alert on potential hallucinations

### Content Filtering

- Filter inappropriate language or content
- Enforce platform-level content policies
- Block or redact sensitive information if detected

## References

- Domain model and AI agent terminology: #[[file:02-domain-model.md]]
- System architecture and integration points: #[[file:03-system-architecture.md]]
- Security and secret management: #[[file:07-security.md]]
- Testing strategies for AI components: #[[file:08-testing.md]]
- Coding standards: #[[file:04-coding-standards.md]]

## Document Boundaries

This document defines AI-specific patterns and integration practices only. It establishes how AI capabilities are integrated, how the RAG pipeline operates, and how knowledge is managed.

**This document must never contain:**

- **General system architecture**: Layered architecture, module boundaries, or dependency rules belong in #[[file:03-system-architecture.md]].
- **Business domain definitions**: Entity definitions, relationships, or business rules belong in #[[file:02-domain-model.md]].
- **Implementation code**: Specific code examples, function implementations, or algorithms belong in implementation files.
- **General security policies**: Authentication, authorization, or general security rules belong in #[[file:07-security.md]].
- **General testing strategies**: Testing philosophy, test types, or coverage requirements belong in #[[file:08-testing.md]].

This document focuses exclusively on **AI integration** (provider patterns, abstractions), **RAG pipeline** (retrieval, generation, scoping), **knowledge management** (chunking, embedding, search), **prompt management** (structure, construction), and **AI-specific quality** (hallucination detection, response validation).

When questions arise about other topics, refer to the appropriate steering document.
