# TX AI Lab — Knowledge, Data and Agent Platform

> **الحالة:** Architecture Direction / Controlled Pilot
> **المنتج الأول:** Athkachatbots
> **نموذج التنفيذ الحالي:** Repository واحد + Modular Monolith بحدود معمارية واضحة
> **الهدف:** بناء منصة مشتركة للمختبر تخدم Athkachatbots ومنتجات AI أخرى مستقبلًا، دون إعادة بناء المعرفة والوكلاء والتقييم من الصفر لكل منتج.

---

## 1. لماذا تغيّر تصور المشروع؟

بدأ المشروع كمنصة **Athkachatbots** لإنشاء Chatbots متعددة العملاء:

```text
Platform Admin
→ Tenant
→ Agent / Chatbot
→ Knowledge Base
→ Documents
→ Ingestion
→ RAG
→ Widget
→ Conversations
```

هذا أثبت نجاحه كـ **Controlled Pilot**.

لكن التصور الجديد أوسع:

```text
Athkachatbots ≠ كامل منصة مختبر الذكاء الاصطناعي

Athkachatbots = أول Product
يعمل فوق خدمات مشتركة للمختبر
```

لذلك سنفصل معماريًا بين:

1. **Knowledge Platform**
2. **Agent Runtime Platform**
3. **Evaluation & Training Platform**
4. **Shared Platform Services**
5. **Products** مثل Athkachatbots

هذا الفصل لا يعني إنشاء 3 مشاريع منفصلة الآن، ولا 3 خوادم، ولا 3 قواعد بيانات.

في المرحلة الحالية سيبقى التنفيذ **مشروعًا برمجيًا واحدًا** منظمًا إلى Modules واضحة، ويمكن لاحقًا استخراج أي Module إلى Service مستقل فقط عندما يوجد سبب فعلي متعلق بالحجم أو الأمن أو فرق التطوير.

---

# 2. الرؤية العامة

```text
                        TX AI Lab Platform
                              │
           ┌──────────────────┼──────────────────┐
           │                  │                  │
           ▼                  ▼                  ▼
  Knowledge Platform    Agent Runtime      Evaluation &
                                            Training
           │                  │                  │
           └──────────────────┼──────────────────┘
                              │
                    Shared Platform Services
                              │
                 ┌────────────┴────────────┐
                 │                         │
                 ▼                         ▼
            Athkachatbots              Future AI
             Product #1                Products
```

## الفكرة الأساسية

نبني الخدمات المشتركة مرة واحدة:

- إدارة المعرفة.
- إدارة الوكلاء.
- RAG.
- Providers.
- التقييم.
- العزل متعدد العملاء.
- التدقيق.
- التخزين.
- المراقبة.
- التكلفة.

ثم تستخدمها المنتجات المختلفة حسب الصلاحيات والحاجة.

---

# 3. ما هو Athkachatbots بعد إعادة التنظيم؟

Athkachatbots سيبقى **منتج SaaS / Managed Service للـChatbots**.

مسؤولياته:

- واجهة Platform Admin.
- واجهة العميل Customer Portal.
- Chatbot Wizard.
- Widget.
- إعداد شكل الـWidget.
- ربط الـWidget بموقع العميل.
- تجربة العميل التجارية.
- إدارة Chatbots الخاصة بالعميل.
- عرض المحادثات المتعلقة بالمنتج.
- أي Billing / Plans مستقبلية تخص المنتج.

لكنه **لن يملك منطق المعرفة أو الذكاء الاصطناعي حصريًا داخله**.

مثال:

```text
Athkachatbots UI
      │
      ├── يستخدم Knowledge Platform
      ├── يستخدم Agent Runtime
      └── يستخدم Evaluation Platform
```

---

# 4. الحالة الحالية المؤكدة للمشروع

## 4.1 المكدس التقني الحالي

```text
Frontend:
- Next.js
- React
- TypeScript

Backend:
- FastAPI
- Python

Data:
- PostgreSQL 16
- pgvector

Runtime:
- Redis
- Ingestion Worker
- Docker Compose
- Alembic

AI:
- DeepSeek للتوليد
- Voyage voyage-4-large للـEmbeddings
- Voyage rerank-2.5 للـReranking
```

## 4.2 ما يعمل حاليًا

```text
Multi-Tenant
Admin Authentication
Admin RBAC
Tenant Management
Agent Management
Knowledge Bases
Documents
Chunks
Ingestion Jobs
Document Upload
Document Replacement
Safe Knowledge Activation
Knowledge ↔ Agent Assignment
Voyage Document Embeddings
Voyage Query Embeddings
pgvector Retrieval
Voyage Reranking
DeepSeek Generation
Grounded RAG
Sources / Citations
Conversations
Messages
Widget Settings
Allowed Origins
Widget Bootstrap
Short-Lived Widget Token
Widget Preview
Website Pairing / Connector Flow
Audit foundations
```

## 4.3 RAG الحالي

```text
INGESTION

Document
   ↓
Chunking
   ↓
VoyageEmbeddingProvider
input_type="document"
   ↓
voyage-4-large
1024 dimensions
   ↓
PostgreSQL + pgvector


CHAT

Question
   ↓
VoyageEmbeddingProvider
input_type="query"
   ↓
pgvector
Top 20 candidates
   ↓
Voyage Rerank
rerank-2.5
   ↓
Top 5
   ↓
DeepSeek
   ↓
Grounded Answer + Sources
```

---

# 5. حدود المنتج والمنصة

## 5.1 Product Layer

### Athkachatbots

مسؤول عن تجربة المستخدم النهائية:

```text
Customer
→ Create Chatbot
→ Configure Chatbot
→ Attach Knowledge
→ Configure Widget
→ Publish
→ Review Conversations
```

### مستقبلًا

يمكن أن تظهر منتجات أخرى مثل:

```text
HR AI Assistant
Legal AI Assistant
Internal Knowledge Assistant
Sales Assistant
Sector-Specific AI Products
```

هذه المنتجات لا تعيد بناء RAG أو Embeddings أو Evaluation من الصفر.

---

# 6. Knowledge Platform

## 6.1 الهدف

منصة المعرفة هي الطبقة المسؤولة عن:

```text
Data Source
→ Ingestion
→ Validation
→ Classification
→ Versioning
→ Approval
→ Chunking
→ Embedding
→ Indexing
→ Retrieval
→ Update / Delete / Archive
```

هي ليست "صفحة رفع ملفات للـChatbot" فقط.

هي نظام إدارة دورة حياة المعرفة للمختبر.

## 6.2 مسؤوليات Knowledge Platform

### مصادر البيانات

يجب أن تدعم مستقبلًا:

- PDF.
- Word.
- Text / Markdown.
- CSV والبيانات المنظمة.
- صفحات ويب.
- APIs.
- قواعد بيانات داخلية.
- صور ومستندات تحتاج OCR.
- مصادر قطاعية داخلية.

### Ingestion

```text
Source
  ↓
Upload / Connector
  ↓
Validation
  ↓
Extract Text
  ↓
OCR عند الحاجة
  ↓
Cleaning
  ↓
Deduplication
  ↓
Metadata
  ↓
Chunking
  ↓
Embedding
  ↓
Index
```

### Metadata

كل أصل معرفي يجب أن يمكن ربطه مستقبلًا بـ:

```text
owner
sector
tenant
source
classification
version
approval_status
created_by
updated_by
retention_policy
effective_date
expiry_date
```

## 6.3 One Fact — One Owner

```text
الجهة التي أنشأت البيانات
        │
        ▼
تظل مالكها التجاري والوظيفي
        │
        ▼
TX AI Lab يدير المعالجة والمنصة
        │
        ▼
المنتجات تحصل على Permission للاستخدام
```

لا تصبح بيانات قطاع ما ملكًا لـAthkachatbots لمجرد استخدامها بواسطة Chatbot.

## 6.4 Knowledge Lifecycle المستهدف

```text
DRAFT
  ↓
REVIEW
  ↓
APPROVED
  ↓
PUBLISHED
  ↓
ACTIVE
  ↓
SUPERSEDED / ARCHIVED / DELETED
```

### تحديث مستند

```text
Version 1 ACTIVE
      │
      ├── رفع Version 2
      ├── Processing
      ├── Embedding
      └── Validation
              │
         ┌────┴────┐
         │         │
       Success    Fail
         │         │
         ▼         ▼
 Atomic switch    V1 remains active
 V2 becomes active
```

## 6.5 الحذف

عند حذف بيانات عميل يجب حذفها من:

```text
Metadata
Documents
Object Storage
Chunks
Embeddings
Indexes
Operational Copies
Caches where applicable
```

مع Audit واضح.

---

# 7. Agent Runtime Platform

## 7.1 الهدف

هذه الطبقة تشغّل الوكلاء فعليًا.

```text
User Message
   ↓
Agent Runtime
   ↓
Context
   ↓
Knowledge Retrieval
   ↓
Tools
   ↓
Model Router
   ↓
Generation
   ↓
Guardrails
   ↓
Response
```

## 7.2 Agent

الـAgent يجب أن يصبح كيانًا عامًا يمكن أن تستخدمه منتجات مختلفة.

```text
Agent
├── tenant_id
├── product_id
├── name
├── role
├── status
├── system_prompt
├── prompt_version
├── knowledge_policy
├── model_policy
├── tool_policy
├── memory_policy
├── budget_policy
└── safety_policy
```

## 7.3 Prompt Management

```text
Prompt
├── Version 1
├── Version 2
├── Version 3
└── Active Version
```

كل محادثة مهمة يجب مستقبلًا أن نعرف:

```text
أي Agent؟
أي Prompt Version؟
أي Model؟
أي Knowledge Version؟
```

---

# 8. Model Provider Abstraction

لا يجب أن يعتمد النظام معماريًا على DeepSeek وحده.

```text
              Model Router
                   │
       ┌───────────┼───────────┐
       │           │           │
       ▼           ▼           ▼
  DeepSeek      Provider B   Open Source
                              مستقبلاً
```

## 8.1 Generation Provider

```text
GenerationProvider
    generate(...)
```

## 8.2 Embedding Provider

```text
EmbeddingProvider
    embed_documents(...)
    embed_query(...)
```

## 8.3 Rerank Provider

```text
RerankProvider
    rerank(...)
```

## 8.4 لماذا؟

حتى نستطيع:

- تغيير النموذج.
- مقارنة التكلفة.
- مقارنة الجودة.
- Failover.
- تعطيل مزود.
- استخدام نموذج محلي مستقبلًا.
- تحديد Model Policy حسب المنتج أو العميل.

---

# 9. Model Routing

```text
Simple FAQ
→ Model A أرخص

Complex reasoning
→ Model B أقوى

Sensitive workflow
→ Approved Provider

Provider outage
→ Fallback Provider
```

يعتمد القرار على:

```text
quality
latency
cost
availability
data classification
tenant policy
```

---

# 10. RAG داخل Agent Runtime

```text
Question
   ↓
Tenant / Agent Scope
   ↓
Permission Check
   ↓
Query Embedding
   ↓
Candidate Retrieval
   ↓
Reranking
   ↓
Evidence Selection
   ↓
Answerability Check
   ↓
Generation
   ↓
Citation Validation
```

أهم قاعدة:

```text
لا Retrieval عبر Tenant boundary
```

---

# 11. Knowledge Modes

### Required

```text
No evidence
→ No factual answer
→ Safe fallback
```

مناسب لخدمة العملاء والسياسات والأسعار.

### Preferred

```text
Evidence available
→ Use it

No evidence
→ Model may answer under product policy
```

### Disabled

بدون Knowledge Retrieval.

---

# 12. Evaluation & Training Platform

هذه ليست منصة لتدريب LLM من الصفر.

هدفها:

```text
قياس
مقارنة
تتبع
تحضير بيانات
واتخاذ قرار
```

## 12.1 Dataset Registry

```text
Dataset
├── name
├── owner
├── domain
├── version
├── status
├── classification
└── records
```

أمثلة:

```text
Sufra Restaurant Evaluation v1
Arabic Customer Support v1
Yemeni Dialect QA v1
```

## 12.2 Golden Questions

```text
Question
Expected Answer
Expected Source
Allowed Variations
Forbidden Claims
Category
Difficulty
Language
Dialect
```

## 12.3 Evaluation Run

```text
Dataset
   ↓
Agent Version
   ↓
Prompt Version
   ↓
Knowledge Version
   ↓
Model
   ↓
Run
   ↓
Metrics
```

## 12.4 Metrics

```text
Retrieval Recall
Retrieval Precision
Answer Correctness
Groundedness
Hallucination Rate
Citation Accuracy
Refusal Accuracy
Arabic Quality
Dialect Quality
Latency
Token Usage
Cost
Failure Rate
```

## 12.5 التجارب

```text
Experiment #42

Dataset:
Sufra-v1

A:
DeepSeek + Prompt v3

B:
Provider B + Prompt v3

Compare:
- correctness
- hallucination
- latency
- cost
```

---

# 13. Training / Fine-Tuning

لا شراء GPU الآن.

```text
Production / Evaluation Data
        ↓
Governance
        ↓
Approved Dataset
        ↓
Cleaning
        ↓
Labeling
        ↓
Dataset Version
        ↓
Fine-Tuning الحاجة مثبتة؟
        │
    ┌───┴───┐
    │       │
   No      Yes
    │       │
  Stop    Rent GPU
            ↓
          Train
            ↓
         Evaluate
            ↓
        Production Gate
```

لا تستخدم بيانات العملاء في التدريب تلقائيًا.

---

# 14. Shared Platform Services

```text
shared/
├── tenants
├── identity
├── auth
├── permissions
├── audit
├── storage
├── secrets
├── observability
├── rate_limits
├── quotas
├── cost
└── notifications
```

---

# 15. Multi-Tenant Architecture

النموذج الحالي:

```text
Shared Database
Shared Tables
tenant_id
```

المبدأ:

```text
Request
   ↓
Authenticated Identity
   ↓
Resolve Tenant
   ↓
Tenant Context
   ↓
Repository / Service
   ↓
tenant_id filtering REQUIRED
```

## 15.1 أنواع العزل المحتملة مستقبلًا

### Shared Tables

```text
Tenant A ┐
Tenant B ├── Shared PostgreSQL
Tenant C ┘      + tenant_id
```

### Schema per Tenant

أقوى لكن أكثر تعقيدًا.

### Database per Tenant

لبعض العملاء ذوي الحساسية العالية.

### Hybrid

```text
Standard customers
→ Shared DB

Regulated / high sensitivity
→ Isolated DB
```

---

# 16. Object Storage

```text
PostgreSQL
→ metadata
→ ownership
→ permissions
→ versions
→ chunks
→ vector metadata

Object Storage
→ original files
→ derived files
→ exported datasets
→ backups where applicable
```

---

# 17. الأمن

يجب أن يغطي التصميم:

- Tenant isolation.
- RBAC.
- Admin permissions.
- API authentication.
- Widget session tokens.
- Rate limiting.
- Allowed Origins.
- Audit.
- Secret management.
- TLS في الوصول العام.
- PII / Sensitive Data classification.
- Provider data policies.
- Prompt injection defenses.
- Retrieval injection defenses.
- File validation.
- Malware scanning عند الحاجة.
- Encryption.
- Key rotation.

---

# 18. حماية البيانات قبل AI Providers

```text
Input
  ↓
Classification
  ↓
Policy Check
  │
  ├── Allowed externally
  │        ↓
  │     Provider
  │
  └── Restricted
           ↓
     Block / Redact /
     Approved provider /
     Local model
```

---

# 19. Conversations & Memory

## Short-Term Context

سياق المحادثة الحالية.

## Long-Term Memory

لا يتم تفعيله بشكل عام بدون سياسة واضحة.

يجب تحديد:

```text
what is stored
why it is stored
who owns it
retention
deletion
sensitivity
```

---

# 20. Observability

كل طلب AI مهم يجب أن ينتج Telemetry:

```text
request_id
tenant_id
product_id
agent_id
conversation_id
model_provider
model_name
prompt_version
knowledge_version
retrieval_count
rerank_count
source_count
answer_status
input_tokens
output_tokens
latency_ms
estimated_cost
error_type
timestamp
```

---

# 21. Cost Management

```text
Infrastructure Cost
+ LLM
+ Embeddings
+ Reranking
+ Storage
+ Backups
+ Monitoring
+ Network
+ Security
+ Operations
```

ثم:

```text
Cost per Customer
Cost per Active User
Cost per Conversation
Cost per 1M Tokens
AI Cost / Revenue
```

---

# 22. Reliability

الخادم الواحد مقبول كمرشح Pilot فقط، وليس Production Architecture نهائيًا.

نحتاج تحديد:

```text
RPO
RTO
```

مع:

- PostgreSQL backup.
- WAL/PITR عند الحاجة.
- Object Storage backup.
- Off-site encrypted backup.
- Immutable backup.
- Restore tests.
- Full server failure plan.
- Secret recovery.
- Incident responsibilities.

---

# 23. Environments

```text
Development
Staging
Production
```

قد نجمع بعضها مؤقتًا في Pilot لتقليل التكلفة، لكن يجب توثيق المخاطر وحدود الاستخدام ومتى يصبح الفصل إلزاميًا.

---

# 24. Capacity Model

يتم التخطيط على 3 مستويات:

| Scenario | Customers |
|---|---:|
| Pilot | 10 |
| Growth | 100 |
| Scale | 1,000 |

لكل سيناريو نحسب:

```text
Concurrent users
Documents / customer
Knowledge size
Chunks
Vectors
Monthly conversations
Tokens / conversation
Embedding calls
Rerank calls
Storage growth
Database growth
Latency
Worker throughput
```

ونحدد Exit Points مثل:

```text
Single Server
      ↓
Separate DB
      ↓
Separate Workers
      ↓
Horizontal API
      ↓
Dedicated Vector Layer if justified
```

---

# 25. المشروع البرمجي الآن: Repository واحد

في المرحلة الحالية **لا ننشئ 3 Repositories**.

```text
tx-ai-lab-platform/
│
├── backend/
├── frontend/
├── tests/
├── docs/
└── infrastructure/
```

ثم داخل Backend نفصل Domains تدريجيًا.

---

# 26. الهيكل المستهدف المقترح

> تنظيم مستهدف تدريجي، وليس أمرًا لنقل كل الملفات فورًا.

```text
backend/app/
│
├── knowledge/
│   ├── domain/
│   ├── application/
│   ├── repositories/
│   ├── ingestion/
│   ├── retrieval/
│   ├── providers/
│   └── api/
│
├── agents/
│   ├── domain/
│   ├── application/
│   ├── runtime/
│   ├── prompts/
│   ├── models/
│   ├── tools/
│   ├── memory/
│   └── api/
│
├── evaluation/
│   ├── datasets/
│   ├── golden_questions/
│   ├── experiments/
│   ├── metrics/
│   └── api/
│
├── products/
│   └── athkachatbots/
│       ├── application/
│       └── api/
│
└── shared/
    ├── tenancy/
    ├── auth/
    ├── audit/
    ├── storage/
    ├── observability/
    ├── cost/
    └── security/
```

---

# 27. Frontend المستهدف

لا نحتاج 3 مواقع مستقلة في البداية.

```text
frontend/
│
├── Platform Admin
├── Athkachatbots Customer Portal
└── Shared Admin Areas
```

### Platform Admin

```text
Dashboard

Products
└── Athkachatbots

Customers / Tenants

Knowledge
├── Sources
├── Knowledge Bases
├── Documents
├── Versions
└── Ingestion

Agents
├── Agents
├── Prompts
├── Models
└── Runtime

Evaluation
├── Datasets
├── Golden Questions
├── Runs
└── Comparisons

Operations
├── Audit
├── Usage
├── Cost
├── Incidents
└── Settings
```

---

# 28. Athkachatbots Customer Portal

العميل لا يحتاج رؤية كل بنية المختبر.

```text
Overview
Chatbots
Knowledge
Conversations
Widget / Website
Team
Account
```

والواجهة تستخدم APIs المشتركة خلف الستار.

---

# 29. مثال كامل: عميل Athkachatbots

```text
Customer = Restaurant X

        ↓

Athkachatbots
Create Chatbot

        ↓

Agent Runtime
Create Agent

        ↓

Knowledge Platform
Create Knowledge Base

        ↓

Upload restaurant.pdf

        ↓

Knowledge Platform
Extract
Chunk
Embed
Index

        ↓

Agent Runtime
Chat Request

        ↓

Knowledge Platform
Retrieve + Rerank

        ↓

Agent Runtime
DeepSeek

        ↓

Athkachatbots
Widget Reply

        ↓

Evaluation
Measure quality / latency / cost
```

---

# 30. مثال: منتج جديد مستقبلًا

نفترض منتجًا:

```text
Internal HR AI
```

لا نبني RAG وEmbeddings وEvaluation من الصفر.

```text
HR Product
   │
   ├── Knowledge Platform
   ├── Agent Runtime
   └── Evaluation Platform
```

---

# 31. Product Logic vs Platform Logic

## Product Logic

```text
Widget color
Chatbot wizard
Customer onboarding
Pricing plan
Product-specific UI
```

يعيش داخل Athkachatbots.

## Platform Logic

```text
Document lifecycle
Embedding
Retrieval
Model provider
Prompt versions
Evaluation
Tenant security
Audit
```

يجب أن يكون قابلًا لإعادة الاستخدام خارج Athkachatbots.

---

# 32. ما لن نفعله الآن

في Controlled Pilot لا نحتاج:

```text
❌ 3 Microservices مستقلة
❌ Kubernetes
❌ شراء GPU
❌ Vector DB مستقلة بدون benchmark
❌ إعادة كتابة المشروع
❌ فصل كل Tenant في DB مستقلة
❌ Event-driven architecture معقدة
❌ Data Lake ضخم
❌ ML training cluster
```

---

# 33. Controlled Pilot

الحالة الحالية:

```text
Athkachatbots Controlled Pilot
```

هدف الـPilot:

```text
إثبات:
- Product works
- RAG works
- Tenant isolation works
- Widget works
- Cost is measurable
- Latency is acceptable
- Knowledge lifecycle works
- Operations are manageable
```

---

# 34. Pilot Acceptance Criteria

بدل:

```text
"يعمل جيدًا"
```

نستخدم:

```text
Metric
Target
Measured Result
PASS / FAIL
```

أمثلة:

```text
Retrieval accuracy
Hallucination rate
Citation accuracy
P95 latency
Error rate
Cross-tenant leakage
Document update correctness
Document delete correctness
Provider outage behavior
Restore time
Cost / conversation
```

---

# 35. مراحل المشروع الجديدة

## Phase 1 — Architecture & Governance

- Boundaries.
- Ownership.
- Security.
- Data Classification.
- Provider Strategy.
- Capacity.
- Cost.
- Backup.
- DR.
- ADRs.

**Exit Gate:** Architecture v1.0 approved.

## Phase 2 — Controlled Pilot Foundation

```text
PostgreSQL
pgvector
Object Storage
Knowledge ingestion
Agent Runtime
Basic Observability
Basic Backup
```

**Exit Gate:** Foundation ready for measured customer testing.

## Phase 3 — Athkachatbots Pilot

تشغيل عدد محدود من العملاء وقياس:

```text
quality
latency
cost
failures
isolation
knowledge updates
support burden
```

**Exit Gate:** Pilot Acceptance Criteria achieved.

## Phase 4 — Production Readiness

- Backup / restore.
- DR.
- Provider fallback.
- Security hardening.
- Observability.
- Cost controls.
- Incident response.
- Environment separation.
- Production SLIs/SLOs.

**Exit Gate:** Production approval.

## Phase 5 — Shared AI Lab Platform

تعميم المكونات المشتركة على منتجات وقطاعات أخرى بعد إثباتها.

---

# 36. Architecture Decision Records — ADR

مثال:

```text
ADR-001
Use PostgreSQL + pgvector for Pilot
```

كل ADR يحتوي:

```text
Problem
Options
Decision
Reason
Cost
Risks
Revisit Trigger
Owner
Approver
Date
```

أمثلة:

```text
ADR-001 PostgreSQL + pgvector
ADR-002 API-First AI Providers
ADR-003 Shared-Table Multi-Tenancy
ADR-004 Object Storage Separation
ADR-005 Modular Monolith
ADR-006 Model Provider Abstraction
ADR-007 Knowledge Ownership Model
ADR-008 Controlled Pilot Hosting
```

---

# 37. Current vs Target

## Current

```text
Athkachatbots-centered codebase
Multi-tenant chatbot platform
RAG
Knowledge
Widget
Admin
Customer portal in progress
```

## Target

```text
Shared AI Lab Platform
      │
      ├── Knowledge Domain
      ├── Agent Runtime Domain
      ├── Evaluation Domain
      └── Shared Services
              │
              ▼
        Athkachatbots
          Product #1
```

---

# 38. Migration Strategy

لا Rewrite.

```text
Step 1
Freeze known-good Pilot baseline

Step 2
Document current module ownership

Step 3
Introduce interfaces / boundaries

Step 4
Move reusable logic gradually

Step 5
Add Evaluation domain

Step 6
Add governance metadata

Step 7
Add observability + cost telemetry

Step 8
Extract services only if measured need exists
```

---

# 39. أولويات التطوير بعد Pilot Demo

## Priority A — تثبيت Pilot

- Real external HTTPS endpoint.
- Real customer website Widget test.
- Stable deployment.
- Clean Git baseline.
- Backup.
- Logs.
- Health checks.

## Priority B — Architecture Foundations

- Product vs Platform boundaries.
- Provider abstractions.
- Knowledge ownership metadata.
- Prompt versioning design.
- Evaluation data model.
- Telemetry model.

## Priority C — Evaluation

- Dataset Registry.
- Golden Questions.
- Evaluation Runner.
- Retrieval metrics.
- Hallucination metrics.
- Citation metrics.
- Latency.
- Cost.

## Priority D — Production Readiness

- DR.
- Security hardening.
- Provider failure handling.
- Capacity testing.
- Load testing.
- Backup restore tests.
- Cost control.

---

# 40. قاعدة العمل للفريق من الآن

قبل إضافة أي Feature نسأل:

```text
هل هذه Feature تخص Product؟
أم Knowledge؟
أم Agent Runtime؟
أم Evaluation؟
أم Shared Platform؟
```

مثال:

```text
Change Widget color
→ Athkachatbots Product

Version Knowledge Document
→ Knowledge Platform

Add another LLM provider
→ Agent Runtime

Compare two models
→ Evaluation Platform

Tenant audit log
→ Shared Platform
```

---

# 41. قاعدة عدم التكرار

إذا احتاج منتجان نفس المنطق:

```text
Product A ─┐
           ├── same capability
Product B ─┘
```

نفحص هل يجب تحويله إلى:

```text
Shared Platform Capability
```

لكن لا نعمم Feature قبل إثبات أنها مشتركة فعليًا.

---

# 42. مبدأ التوسع

```text
Measure
↓
Find Bottleneck
↓
Change Architecture
↓
Measure Again
```

وليس:

```text
نتوقع 1000 عميل
↓
نبني Kubernetes و20 Service الآن
```

---

# 43. Definition of Production Ready

```text
Functional correctness
Security
Isolation
Backups
Restore
Monitoring
Alerting
Cost control
Capacity
Provider resilience
Incident response
Data governance
Release process
Rollback
Measured acceptance criteria
```

---

# 44. الخلاصة

المشروع لن يتحول إلى ثلاث منصات مستقلة على ثلاثة خوادم.

في المرحلة الحالية سيصبح:

```text
TX AI Lab Platform
        │
        ├── Knowledge Module
        ├── Agent Runtime Module
        ├── Evaluation Module
        ├── Shared Services
        └── Products
             └── Athkachatbots
```

**Repository واحد الآن.**
**قاعدة كود واحدة الآن.**
**حدود معمارية واضحة.**
**لا Rewrite.**
**لا Microservices مبكرة.**

Athkachatbots يستمر كأول Product، بينما نعيد تنظيم القدرات القابلة لإعادة الاستخدام تدريجيًا لتصبح أساسًا مشتركًا للمختبر.

---

# 45. الحالة الرسمية المقترحة

```text
TX AI Lab — Knowledge, Data and Agent Platform
Architecture: In Completion

Athkachatbots
Status: Controlled Pilot

Current Infrastructure
Status: Pilot Candidate

Production Infrastructure
Status: Not Yet Approved
```

---

# 46. الوثائق التي يجب أن ترافق هذا README

```text
docs/
├── architecture/
│   ├── executive-decision.md
│   ├── scope-and-assumptions.md
│   ├── product-platform-boundaries.md
│   ├── target-architecture.md
│   └── current-state.md
│
├── knowledge/
│   ├── lifecycle.md
│   ├── ownership-governance.md
│   └── classification.md
│
├── security/
│   ├── multi-tenant-model.md
│   ├── provider-data-policy.md
│   └── threat-model.md
│
├── evaluation/
│   ├── evaluation-architecture.md
│   ├── metrics.md
│   └── pilot-acceptance.md
│
├── operations/
│   ├── observability.md
│   ├── backup-dr.md
│   ├── incident-response.md
│   └── capacity.md
│
├── cost/
│   └── tco-model.md
│
└── adr/
    ├── ADR-001-pgvector.md
    ├── ADR-002-api-first-models.md
    ├── ADR-003-multi-tenancy.md
    ├── ADR-004-object-storage.md
    └── ADR-005-modular-monolith.md
```

---

# 47. القرار التنفيذي المختصر

إذا سأل أحد:

> ما المشروع الآن؟

الإجابة:

**نحن نبني TX AI Lab Shared Platform تدريجيًا، وAthkachatbots هو أول منتج يعمل فوقها.**

إذا سأل:

> هل Knowledge Platform وAgent Runtime وEvaluation مشاريع منفصلة؟

الإجابة:

**لا في المرحلة الحالية. هي Domains/Modules مستقلة معماريًا داخل نفس المشروع، مع إمكانية فصلها مستقبلًا عند وجود حاجة مثبتة.**

إذا سأل:

> هل نعيد بناء Athkachatbots؟

الإجابة:

**لا. نثبت الـControlled Pilot الحالي ثم نفصل المنطق المشترك تدريجيًا بدون Rewrite.**

إذا سأل:

> ما الأولوية الآن؟

الإجابة:

**إنجاح Pilot مقاس، توثيق Architecture v1.0، ثم إغلاق Production Readiness قبل التوسع.**
