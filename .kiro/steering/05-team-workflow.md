# 05-team-workflow: Team Workflow and Collaboration

## Purpose

This document defines team collaboration practices, Git workflow, task ownership, code review process, and communication patterns for the Modern AI Agent Platform development team. It establishes how three developers work together, manage branches, handle pull requests, coordinate changes, and maintain code quality through review.

## Team Structure

The Modern AI Agent Platform is developed by a three-developer team working collaboratively on backend and frontend components. The team operates with shared ownership of the codebase, clear task boundaries, and structured code review processes.

**Collaboration Model**: Each developer owns specific tasks but reviews others' work. All developers can contribute to any part of the system while respecting existing patterns and conventions.

**Decision-Making**: Technical decisions follow the priority established in #[[file:00-ai-assistant-role.md]]: existing patterns first, then requirements, then architectural principles.

## Task Ownership and Boundaries

### Task Assignment

- Each task has a single owner responsible for implementation and completion
- Task ownership is explicit and tracked in task management system
- Owners are responsible for implementation, testing, documentation, and completion
- Other developers may review, provide feedback, or collaborate, but owner drives completion

### Task Boundaries

- Implement exactly what the task specifies—no scope creep
- Complete all acceptance criteria defined in the task
- Test thoroughly before marking complete
- Update documentation when functionality changes
- Report completion with clear summary of changes

### Respecting Other Developers' Work

When modifying code written by another developer:
1. Explain why the change is necessary
2. Show what you're changing
3. Confirm the change is part of your assigned task scope
4. Reference the task that requires the modification

**Do not**:
- Refactor unrelated code without task justification
- Add unrequested features or improvements
- Redesign architecture beyond task scope
- Make changes "because it's better"—justify with task requirements

## Git Workflow

### Branch Strategy

**Main Branch** (`main`):
- Protected branch requiring pull request approval
- Always deployable and stable
- No direct commits—all changes through pull requests
- Represents production-ready code

**Feature Branches**:
- Created from `main` for each task or feature
- Named descriptively: `feature/agent-management`, `fix/tenant-isolation-query`, `refactor/rag-pipeline`
- One branch per task or closely related group of changes
- Deleted after merge to keep repository clean

**Branch Naming Convention**:
- `feature/description`: New features (e.g., `feature/knowledge-upload`)
- `fix/description`: Bug fixes (e.g., `fix/embedding-generation-timeout`)
- `refactor/description`: Code refactoring (e.g., `refactor/repository-pattern`)
- `docs/description`: Documentation changes (e.g., `docs/api-endpoint-specs`)
- `test/description`: Test-only changes (e.g., `test/tenant-isolation-coverage`)

### Commit Message Format

Use **Conventional Commits** format for all commit messages:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type**:
- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code refactoring without functional changes
- `test`: Adding or modifying tests
- `docs`: Documentation changes
- `style`: Code style changes (formatting, whitespace)
- `chore`: Maintenance tasks (dependencies, build config)

**Scope** (optional): Component or module affected (e.g., `auth`, `agent`, `knowledge`, `rag-pipeline`)

**Subject**: Short description (50 characters max, lowercase, no period)

**Body** (optional): Detailed explanation of changes, motivation, and context

**Footer** (optional): References to issues, breaking changes

**Examples**:
```
feat(agent): add agent creation API endpoint

Implement POST /agents endpoint with tenant isolation.
Includes request validation, repository integration, and unit tests.

Closes #42
```

```
fix(knowledge): correct embedding generation timeout handling

Add retry logic with exponential backoff for embedding API calls.
Prevents knowledge upload failures due to transient provider errors.
```

```
refactor(auth): extract tenant context to middleware

Move tenant context establishment from route handlers to middleware.
Improves code reuse and enforces consistent tenant isolation.
```

### Working with Branches

**Creating a Branch**:
```bash
git checkout main
git pull origin main
git checkout -b feature/your-feature-name
```

**Making Changes**:
```bash
# Make code changes
git add <files>
git commit -m "feat(scope): description"
```

**Keeping Branch Updated**:
```bash
git checkout main
git pull origin main
git checkout feature/your-feature-name
git rebase main
# Resolve conflicts if any
git push --force-with-lease origin feature/your-feature-name
```

**Pushing Branch**:
```bash
git push -u origin feature/your-feature-name
```

## Pull Request Process

### Creating a Pull Request

**Before Creating PR**:
1. Run all tests and ensure they pass
2. Run linters and formatters (`black`, `ruff` for Python; `prettier`, `eslint` for TypeScript)
3. Update documentation if functionality changed
4. Rebase on `main` to ensure clean merge
5. Review your own changes first

**PR Title Format**:
Use the same format as commit messages:
```
feat(agent): add agent creation API endpoint
fix(knowledge): correct embedding generation timeout handling
```

**PR Description Template**:
```markdown
## Summary
[Brief description of what this PR does]

## Changes
- [List key changes made]
- [Affected files or components]
- [New dependencies or configuration changes]

## Testing
- [Tests added or modified]
- [Test results summary]
- [Manual testing performed]

## Related Issues
Closes #[issue number]

## Checklist
- [ ] Tests pass
- [ ] Code follows project conventions
- [ ] Documentation updated
- [ ] Rebased on main
- [ ] Self-reviewed
```

### Code Review Process

**Who Reviews**:
- At least one other developer must approve the PR
- Prefer reviewers familiar with the affected code area
- All developers can review and provide feedback

**Review Criteria**:
- Code correctness and logic
- Test coverage and quality
- Adherence to coding standards (#[[file:04-coding-standards.md]])
- Architectural consistency (#[[file:03-system-architecture.md]])
- Tenant isolation enforcement (all queries scoped by tenant/agent)
- Security considerations (#[[file:07-security.md]])
- Documentation completeness

**Review Guidelines**:
- Focus on correctness, clarity, and maintainability
- Suggest improvements, don't demand perfection
- Distinguish between blocking issues (must fix) and suggestions (nice to have)
- Provide specific, actionable feedback
- Explain the reasoning behind feedback
- Approve when the code meets standards, even if minor improvements are possible

**Reviewer Responsibilities**:
- Review within 24 hours when possible
- Test locally for complex changes
- Verify tests pass
- Check for tenant isolation violations
- Flag security concerns immediately

**Author Responsibilities**:
- Address all feedback or explain why changes aren't needed
- Update PR description when scope changes
- Re-request review after making changes
- Merge only after approval and passing tests

### Merging Pull Requests

**Merge Requirements**:
- At least one approval from another developer
- All tests pass
- No merge conflicts
- Branch is up to date with `main`

**Merge Strategy**:
- Use **squash and merge** for feature branches to keep history clean
- Use descriptive commit message for the squashed commit
- Delete branch after merge

**Merge Command** (if manual):
```bash
git checkout main
git pull origin main
git merge --squash feature/your-feature-name
git commit -m "feat(scope): description"
git push origin main
```

## Code Review Best Practices

### What to Look For

**Correctness**:
- Does the code implement the requirement correctly?
- Are edge cases handled?
- Are error conditions managed appropriately?

**Multi-Tenancy**:
- Are all queries scoped by tenant ID?
- Is agent isolation enforced for knowledge operations?
- Is tenant context propagated correctly?
- No cross-tenant data access possible?

**Code Quality**:
- Functions and classes have single responsibilities?
- Names are descriptive and follow conventions?
- Code is readable and self-explanatory?
- No unnecessary complexity or over-engineering?

**Testing**:
- Unit tests exist for new business logic?
- Tests cover edge cases and error conditions?
- Tests are independent and repeatable?
- Multi-tenant isolation is tested?

**Security**:
- Input validation at API boundaries?
- Authentication and authorization enforced?
- No secrets in code or logs?
- Proper error handling without exposing sensitive data?

**Documentation**:
- Public functions and classes have docstrings?
- Complex logic is explained with comments?
- API changes are documented?

### Providing Feedback

**Be Specific**:
```
❌ "This function is confusing."
✅ "Consider renaming `process_data()` to `retrieve_knowledge_chunks()` to clarify intent."
```

**Be Constructive**:
```
❌ "This is wrong."
✅ "This query is missing tenant_id filter, which could expose cross-tenant data. Add `.filter(Agent.tenant_id == tenant_id)` to line 42."
```

**Distinguish Blocking Issues from Suggestions**:
```
🚫 BLOCKING: "This query allows cross-tenant access. Must add tenant_id filter."
💡 SUGGESTION: "Consider extracting this validation logic to a domain entity method for reuse."
```

**Explain Reasoning**:
```
"This function is doing too much—it retrieves data, validates, transforms, and logs. 
Consider splitting into smaller functions for easier testing and maintenance."
```

### Receiving Feedback

- Assume reviewers have good intentions
- Ask for clarification when feedback is unclear
- Address blocking issues before requesting re-review
- Explain decisions when declining suggestions
- Thank reviewers for their time and input

## Communication Patterns

### When to Communicate

**Always Communicate**:
- When requirements are ambiguous or conflicting
- When blocked by another task or developer
- When making architectural decisions affecting multiple components
- When discovering bugs or issues in existing code
- When changing shared code or interfaces

**Communicate Early**:
- When approaching task completion
- When discovering scope changes needed
- When task dependencies are discovered
- When encountering technical difficulties

**Communicate Proactively**:
- Daily progress updates (what was done, what's next, blockers)
- When deviating from original plan or design
- When introducing new dependencies or tools

### Communication Channels

**Task Comments**:
- Task-specific discussions
- Implementation questions
- Completion reports

**Pull Request Comments**:
- Code-specific feedback
- Implementation discussions
- Clarification requests

**Team Chat**:
- Quick questions
- Coordination and scheduling
- Informal discussions

**Documentation**:
- Architectural decisions
- API specifications
- Process changes

## Dependency Management

### Adding Dependencies

**Before Adding a Dependency**:
1. Check if existing dependencies provide the functionality
2. Verify the package is actively maintained
3. Check license compatibility
4. Assess security and reputation
5. Consider bundle size impact (for frontend)

**Adding Backend Dependencies**:
```bash
# Add to requirements.txt with pinned version
echo "package-name==1.2.3" >> backend/requirements.txt
pip install -r backend/requirements.txt
```

**Adding Frontend Dependencies**:
```bash
cd frontend
npm install package-name@1.2.3
# Commit package.json and package-lock.json
```

**Document New Dependencies**:
- Add rationale in pull request description
- Update README if setup instructions change
- Document configuration if required

### Version Pinning

- Pin exact versions for production dependencies
- Use version ranges only for development dependencies when appropriate
- Update dependencies deliberately, not automatically

## Environment Setup

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with configuration
```

### Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env.local
# Edit .env.local with configuration
```

### Running Tests

**Backend**:
```bash
cd backend
pytest
```

**Frontend**:
```bash
cd frontend
npm test
```

### Running Linters and Formatters

**Backend**:
```bash
cd backend
black .
ruff check .
```

**Frontend**:
```bash
cd frontend
npm run lint
npm run format
```

## Reporting Completed Work

When completing a task, provide:

**Summary**:
- What was implemented
- How it works (briefly)
- Key decisions made

**Files Changed**:
- Files created, modified, or deleted
- Brief description of each change

**Testing**:
- Tests written or updated
- Test results summary

**Documentation**:
- Documentation updated
- New usage examples if applicable

**Questions or Review Items**:
- Anything needing clarification
- Trade-offs made
- Items needing further review

**Example Completion Report**:
```markdown
## Summary
Implemented agent creation API endpoint with tenant isolation.

## Changes
- Created: backend/app/api/routes/agents.py (agent CRUD endpoints)
- Created: backend/app/schemas/agent.py (request/response schemas)
- Modified: backend/app/services/agent_service.py (added create_agent method)
- Created: backend/tests/test_agent_api.py (15 tests covering CRUD and tenant isolation)

## Testing
All 15 tests pass. Coverage includes:
- Agent creation with valid data
- Tenant isolation enforcement
- Input validation
- Error handling

## Documentation
- Added docstrings to all public methods
- Updated API documentation with endpoint details

## Questions
- Should agent names be unique per tenant, or globally unique?
```

## Working with AI Assistance

When working with AI assistants (like Kiro):
- Provide clear task descriptions with acceptance criteria
- Reference relevant steering files for context
- Review generated code before committing
- Verify tests pass and code follows conventions
- Treat AI-generated code as a starting point, not final solution

See #[[file:00-ai-assistant-role.md]] for detailed AI assistant behavior guidelines.

## References

- AI assistant behavior: #[[file:00-ai-assistant-role.md]]
- Code quality requirements: #[[file:04-coding-standards.md]]
- Completion criteria: #[[file:09-definition-of-done.md]]
- Testing requirements: #[[file:08-testing.md]]
- Security requirements: #[[file:07-security.md]]
- Architecture patterns: #[[file:03-system-architecture.md]]

## Document Boundaries

This document defines team workflow and collaboration practices only. It establishes how developers work together, manage code, and coordinate changes.

**This document must never contain:**

- **Code implementation**: Specific code examples, function implementations, or detailed algorithms.
- **Architecture design**: System layers, component relationships, or technical architecture.
- **Domain definitions**: Business entities, domain rules, or ubiquitous language.
- **Coding standards**: Language-specific conventions, naming rules, or code organization patterns.
- **Testing implementation**: Test frameworks, specific test cases, or testing techniques.

This document focuses exclusively on **collaboration** (how developers work together), **Git workflow** (branching, commits, merges), **code review** (process and criteria), and **communication** (when and how to communicate).

When questions arise about other topics, refer to the appropriate steering document.
