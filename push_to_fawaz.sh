#!/bin/bash
# Script to push changes to fawaz branch (excluding .kiro)

set -e  # Exit on error

echo "================================================"
echo "🚀 Pushing to fawaz branch (excluding .kiro)"
echo "================================================"

# Navigate to project directory
cd "/home/yawelcome/Documents/Travie x  info/saas ai agent new/Modern-Ai-Agent-Platform"

echo ""
echo "🗑️  Step 1: Removing .kiro from git tracking (if tracked)..."
git rm -r --cached .kiro 2>/dev/null || echo ".kiro not tracked, skipping..."

echo ""
echo "📋 Step 2: Checking current status..."
git status

echo ""
echo "📦 Step 3: Adding all changes (excluding .kiro)..."
git add .

echo ""
echo "💾 Step 4: Creating commit..."
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
echo "🌿 Step 5: Switching to fawaz branch..."
git checkout -b fawaz 2>/dev/null || git checkout fawaz

echo ""
echo "📤 Step 6: Pushing to GitHub (fawaz branch)..."
git push -u origin fawaz

echo ""
echo "================================================"
echo "✅ SUCCESS! Changes pushed to fawaz branch"
echo "================================================"
echo ""
echo "Branch: fawaz"
echo "Excluded: .kiro/ directory"
echo ""
echo "Next steps:"
echo "1. Go to your GitHub repository"
echo "2. Verify fawaz branch has your changes"
echo "3. Create Pull Request if needed"
echo ""
