#!/bin/bash
# Script to push changes to GitHub

set -e  # Exit on error

echo "================================================"
echo "🚀 Pushing Secure Chat API to GitHub"
echo "================================================"

# Navigate to project directory
cd "/home/yawelcome/Documents/Travie x  info/saas ai agent new/Modern-Ai-Agent-Platform"

echo ""
echo "📋 Step 1: Checking current status..."
git status

echo ""
echo "📦 Step 2: Adding all changes..."
git add -A

echo ""
echo "💾 Step 3: Creating commit..."
git commit -m "feat: Add secure multi-tenant chat API with authentication

- Implement API key authentication with bcrypt hashing
- Add tenant context extraction and isolation
- Create database models (Client, Agent, ApiKey, Conversation, Message)
- Build chat service connecting API to LangGraph Core AI Runtime
- Add rate limiting per API key (60 req/min configurable)
- Implement idempotency key handling
- Add CORS configuration with allowlist
- Structured logging without sensitive data
- Unified error handling without traceback exposure
- Comprehensive test suite covering auth, isolation, security
- POST /v1/chat endpoint with tenant validation
- GET /v1/conversations/{id} with ownership check
- GET /v1/conversations/{id}/messages with tenant isolation

See DELIVERY_REPORT.md for complete documentation." || echo "Already committed or nothing to commit"

echo ""
echo "🌿 Step 4: Switching to feature branch..."
git checkout -b feature/secure-chat-api 2>/dev/null || git checkout feature/secure-chat-api

echo ""
echo "📤 Step 5: Pushing to GitHub..."
git push -u origin feature/secure-chat-api

echo ""
echo "================================================"
echo "✅ SUCCESS! Changes pushed to GitHub"
echo "================================================"
echo ""
echo "Branch: feature/secure-chat-api"
echo ""
echo "Next steps:"
echo "1. Go to your GitHub repository"
echo "2. Create a Pull Request from feature/secure-chat-api to main"
echo "3. Review DELIVERY_REPORT.md before merging"
echo ""
echo "Or create PR using GitHub CLI:"
echo "gh pr create --title 'Secure Multi-Tenant Chat API' --body 'See DELIVERY_REPORT.md for complete details'"
echo ""
