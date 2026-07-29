# 🚀 Quick Start Guide - Secure Chat API

## Branch: `feature/secure-chat-api`

## 📦 Installation

```bash
cd backend
pip install -r requirements.txt
```

## 🗄️ Setup Database & Test Data

```bash
python create_test_data.py
```

**Output will give you**:
- Client ID: `demo-client-1`
- Agent ID: `demo-agent-1`  
- API Key: `demo-api-key-12345678`

## 🏃 Run Server

```bash
uvicorn backend.app.main:app --reload --port 8000
```

Server runs at: `http://localhost:8000`

## 🧪 Test the API

### Send a Message
```bash
curl -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: demo-api-key-12345678" \
  -d '{
    "agent_id": "demo-agent-1",
    "message": "Hello! How can you help me today?"
  }'
```

### Get Conversation
```bash
curl -X GET http://localhost:8000/v1/conversations/{conversation_id} \
  -H "X-API-Key: demo-api-key-12345678"
```

### Get Messages
```bash
curl -X GET http://localhost:8000/v1/conversations/{conversation_id}/messages \
  -H "X-API-Key: demo-api-key-12345678"
```

## 🧪 Run Tests

```bash
cd backend
python -m pytest tests/ -v
```

Expected: 48+ tests passing

## 📖 Full Documentation

See `DELIVERY_REPORT.md` for complete details on:
- Architecture
- Security implementation
- API endpoints
- Integration with LangGraph
- Test coverage
- Deployment guide

## ⚠️ Important Notes

- **SQLite** used for development (use PostgreSQL in production)
- **In-memory** rate limiting (use Redis in production)
- **DeepSeek API key** needed in `.env` for real AI responses
- **Ollama** must be running locally for embeddings

## 🔐 Security Features

✅ API key authentication with bcrypt  
✅ Multi-tenant isolation  
✅ Rate limiting (60 req/min)  
✅ Idempotency support  
✅ CORS configuration  
✅ No sensitive data in logs  
✅ Safe error responses  

## 📝 Environment Variables

Copy `.env.example` to `.env` and set:
```bash
MAAP_DEEPSEEK_API_KEY=your-key-here
MAAP_DATABASE_URL=sqlite:///./maap.db
MAAP_CORS_ORIGINS=["http://localhost:3000"]
```

---

**Ready to integrate!** 🎉
