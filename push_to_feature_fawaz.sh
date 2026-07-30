#!/bin/bash
# Script to push changes to feature/fawaz branch (excluding .kiro)

set -e  # Exit on error

echo "================================================"
echo "🚀 Pushing to feature/fawaz branch"
echo "================================================"

cd "/home/yawelcome/Documents/Travie x  info/saas ai agent new/Modern-Ai-Agent-Platform"

echo ""
echo "🗑️  Removing .kiro from tracking..."
git rm -r --cached .kiro 2>/dev/null || echo ".kiro not tracked"

echo ""
echo "📦 Adding all changes (excluding .kiro)..."
git add .

echo ""
echo "💾 Creating commit..."
git commit -m "feat: Add secure multi-tenant chat API with authentication

- API key authentication with bcrypt hashing
- Multi-tenant isolation
- Database models (Client, Agent, ApiKey, Conversation, Message)
- Chat service connecting to LangGraph
- Rate limiting (60 req/min)
- Idempotency handling
- CORS configuration
- Secure logging
- Error handling
- Comprehensive tests (48+)
- POST /v1/chat
- GET /v1/conversations endpoints

See DELIVERY_REPORT.md" || echo "Nothing to commit"

echo ""
echo "🌿 Switching to feature/fawaz branch..."
git checkout -b feature/fawaz 2>/dev/null || git checkout feature/fawaz

echo ""
echo "📤 Pushing to GitHub..."
git push -u origin feature/fawaz --force

echo ""
echo "================================================"
echo "✅ SUCCESS! Pushed to feature/fawaz"
echo "================================================"
