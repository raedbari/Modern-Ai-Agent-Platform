# 09-definition-of-done: Completion Criteria

## Purpose

This document defines the completion criteria for work in the Modern AI Agent Platform. It establishes what "done" means for features, bug fixes, and releases. This document ensures consistent quality standards and prevents incomplete work from being marked as complete.

## What is "Done"?

Work is "done" when it meets all completion criteria and is ready for production use. Done work is:
- Functionally complete (implements all requirements)
- Tested (passes all tests, meets coverage requirements)
- Documented (code is clear, public APIs are documented)
- Reviewed (approved by at least one other developer)
- Merged (integrated into main branch)
- Deployable (can be released to production safely)

**Incomplete work is not done.** Work that is "mostly done" or "done except for tests" is not done.

## Definition of Done: Features

A feature is done when all of the following criteria are met:

### 1. Requirements Met

- [ ] All acceptance criteria from requirements are implemented
- [ ] Feature behaves as specified in design document
- [ ] Edge cases are handled appropriately
- [ ] Error conditions are handled correctly

### 2. Code Quality

- [ ] Code follows project coding standards (#[[file:04-coding-standards.md]])
- [ ] Code is readable and maintainable
- [ ] No code duplication without justification
- [ ] Functions and classes have single responsibilities
- [ ] Names are descriptive and follow naming conventions
- [ ] Type hints (Python) or type annotations (TypeScript) are complete
- [ ] No commented-out code or debug statements

### 3. Multi-Tenancy and Security

- [ ] Tenant context is established and propagated correctly
- [ ] All queries are scoped by tenant ID (and agent ID when applicable)
- [ ] Tenant ownership is verified before operations
- [ ] No cross-tenant data access is possible
- [ ] Agent isolation is enforced for knowledge operations (#[[file:06-ai-platform.md]])
- [ ] Authentication and authorization are enforced (#[[file:07-security.md]])
- [ ] Input validation is implemented at API boundaries
- [ ] Secrets are not hardcoded or logged

### 4. Testing

- [ ] Unit tests are written for business logic
- [ ] Unit test coverage meets minimum threshold (80%)
- [ ] Integration tests are written for API endpoints and workflows
- [ ] Integration test coverage meets minimum threshold (70%)
- [ ] Tests cover edge cases and error conditions
- [ ] Tests verify tenant isolation
- [ ] Property-based tests are written (if applicable)
- [ ] All tests pass locally
- [ ] All tests pass in CI/CD pipeline

See #[[file:08-testing.md]] for detailed testing requirements.

### 5. Documentation

- [ ] Public functions and classes have docstrings (Python) or JSDoc (TypeScript)
- [ ] Complex logic is explained with comments
- [ ] API changes are documented
- [ ] README is updated if setup or usage changes
- [ ] Breaking changes are clearly marked and documented

### 6. Code Review

- [ ] Pull request is created with clear description
- [ ] At least one other developer has reviewed the code
- [ ] All review feedback is addressed or discussed
- [ ] Reviewer has approved the pull request
- [ ] No unresolved review comments

See #[[file:05-team-workflow.md]] for code review process.

### 7. Integration

- [ ] Code is rebased on main branch
- [ ] No merge conflicts
- [ ] All tests pass after rebase
- [ ] Code is merged into main branch
- [ ] Feature branch is deleted

### 8. Deployment Readiness

- [ ] No breaking changes without migration plan
- [ ] Configuration changes are documented
- [ ] Database migrations are created (if needed)
- [ ] Rollback plan exists (if applicable)
- [ ] Feature can be deployed to production safely

---

## Definition of Done: Bug Fixes

A bug fix is done when all of the following criteria are met:

### 1. Bug Reproduction

- [ ] Bug is reproducible and understood
- [ ] Root cause is identified
- [ ] Impact is assessed (affected users, data, features)

### 2. Fix Implementation

- [ ] Bug is fixed at the root cause (not just symptoms)
- [ ] Fix does not introduce new bugs or regressions
- [ ] Fix follows project coding standards
- [ ] Fix is minimal and focused (no scope creep)

### 3. Regression Prevention

- [ ] Test is written to prevent bug recurrence
- [ ] Test reproduces the bug before the fix
- [ ] Test passes after the fix
- [ ] Test is added to test suite

### 4. Testing

- [ ] All existing tests still pass
- [ ] Regression test is written for the bug
- [ ] Related functionality is tested
- [ ] Edge cases related to the bug are tested

### 5. Documentation

- [ ] Bug fix is documented in commit message
- [ ] If bug affects users, release notes mention the fix
- [ ] If behavior changes, documentation is updated

### 6. Code Review

- [ ] Pull request is created with clear description
- [ ] Root cause and fix are explained
- [ ] At least one other developer has reviewed the fix
- [ ] Reviewer has approved the pull request

### 7. Integration

- [ ] Code is merged into main branch
- [ ] Bug fix is verified in integration environment
- [ ] Bug fix can be deployed to production

---

## Definition of Done: Releases

A release is done when all of the following criteria are met:

### 1. Code Stability

- [ ] All tests pass in CI/CD pipeline
- [ ] Code coverage meets minimum thresholds
- [ ] No known critical bugs in release scope
- [ ] No unresolved merge conflicts
- [ ] Main branch is stable and deployable

### 2. Release Preparation

- [ ] Release version is determined (semantic versioning)
- [ ] Release notes are written (features, bug fixes, breaking changes)
- [ ] Database migrations are tested (if applicable)
- [ ] Configuration changes are documented
- [ ] Deployment plan is documented
- [ ] Rollback plan is documented

### 3. Testing

- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] All end-to-end tests pass
- [ ] Manual testing of critical workflows is performed
- [ ] Release candidate is tested in staging environment

### 4. Documentation

- [ ] User-facing documentation is updated
- [ ] API documentation is updated
- [ ] Deployment documentation is updated
- [ ] Breaking changes are clearly documented
- [ ] Migration guides are provided (if needed)

### 5. Deployment

- [ ] Release is deployed to staging environment
- [ ] Staging deployment is verified
- [ ] Release is deployed to production environment
- [ ] Production deployment is verified
- [ ] Monitoring and alerting are active

### 6. Communication

- [ ] Release notes are published
- [ ] Team is notified of release
- [ ] Users are notified (if user-facing changes)
- [ ] Support team is briefed (if applicable)

---

## Completion Checklist Templates

### Feature Completion Checklist

Use this checklist when completing a feature:

```markdown
## Feature: [Feature Name]

### Requirements
- [ ] All acceptance criteria implemented
- [ ] Feature behaves as designed
- [ ] Edge cases handled
- [ ] Error conditions handled

### Code Quality
- [ ] Follows coding standards
- [ ] Readable and maintainable
- [ ] No duplication
- [ ] Type hints/annotations complete

### Multi-Tenancy & Security
- [ ] Tenant context propagated
- [ ] Queries scoped by tenant/agent
- [ ] Tenant ownership verified
- [ ] No cross-tenant access
- [ ] Authentication enforced
- [ ] Input validated
- [ ] No secrets in code/logs

### Testing
- [ ] Unit tests written (80% coverage)
- [ ] Integration tests written (70% coverage)
- [ ] Edge cases tested
- [ ] Tenant isolation tested
- [ ] All tests pass

### Documentation
- [ ] Public APIs documented
- [ ] Complex logic explained
- [ ] README updated
- [ ] Breaking changes documented

### Review & Integration
- [ ] Pull request created
- [ ] Reviewed and approved
- [ ] Rebased on main
- [ ] Merged to main
- [ ] Branch deleted

### Deployment Readiness
- [ ] No breaking changes without migration
- [ ] Configuration documented
- [ ] Deployable to production
```

### Bug Fix Completion Checklist

Use this checklist when fixing a bug:

```markdown
## Bug Fix: [Bug Description]

### Bug Understanding
- [ ] Bug reproduced
- [ ] Root cause identified
- [ ] Impact assessed

### Fix Implementation
- [ ] Root cause fixed
- [ ] No new bugs introduced
- [ ] Follows coding standards
- [ ] Minimal and focused

### Regression Prevention
- [ ] Regression test written
- [ ] Test reproduces bug before fix
- [ ] Test passes after fix
- [ ] Test added to suite

### Testing
- [ ] All existing tests pass
- [ ] Related functionality tested
- [ ] Edge cases tested

### Documentation
- [ ] Fix documented in commit
- [ ] Release notes updated (if user-facing)
- [ ] Documentation updated (if behavior changed)

### Review & Integration
- [ ] Pull request created
- [ ] Root cause explained
- [ ] Reviewed and approved
- [ ] Merged to main
- [ ] Verified in integration
```

### Release Completion Checklist

Use this checklist when preparing a release:

```markdown
## Release: [Version Number]

### Code Stability
- [ ] All tests pass in CI/CD
- [ ] Coverage meets thresholds
- [ ] No critical bugs
- [ ] Main branch stable

### Release Preparation
- [ ] Version determined
- [ ] Release notes written
- [ ] Migrations tested
- [ ] Configuration documented
- [ ] Deployment plan documented
- [ ] Rollback plan documented

### Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] End-to-end tests pass
- [ ] Critical workflows tested manually
- [ ] Staging environment verified

### Documentation
- [ ] User docs updated
- [ ] API docs updated
- [ ] Deployment docs updated
- [ ] Breaking changes documented
- [ ] Migration guides provided

### Deployment
- [ ] Deployed to staging
- [ ] Staging verified
- [ ] Deployed to production
- [ ] Production verified
- [ ] Monitoring active

### Communication
- [ ] Release notes published
- [ ] Team notified
- [ ] Users notified
- [ ] Support team briefed
```

---

## Exceptions and Flexibility

### When Exceptions Are Acceptable

Completion criteria are non-negotiable for production features and releases. However, exceptions may be acceptable in the following cases:

**Prototypes and Experiments**:
- Incomplete tests for proof-of-concept code
- Documentation may be minimal
- Code quality standards may be relaxed
- Must be clearly marked as experimental

**Urgent Hotfixes**:
- Critical security vulnerabilities may require immediate deployment
- Tests may be added after deployment (but must be added)
- Documentation may be minimal initially
- Must be followed up with complete testing and documentation

**Technical Debt**:
- Knowingly incomplete work may be merged if:
  - It is explicitly documented as technical debt
  - A follow-up task is created to address the debt
  - The incomplete work does not affect production users
  - Team agrees to the trade-off

**Exceptions Must Be Documented**:
- Explain why the exception is necessary
- Describe what is incomplete
- Create follow-up tasks
- Get team approval

### When Exceptions Are NOT Acceptable

**Never skip these criteria**:
- Tenant isolation and security checks
- Input validation at API boundaries
- Authentication and authorization
- Basic functionality testing
- Code review

**No exceptions for**:
- Cross-tenant data access vulnerabilities
- Security vulnerabilities
- Data corruption risks
- Breaking changes without migration plan

---

## Measuring Completeness

### How to Know If Work Is Done

Ask these questions:
- Does it implement all requirements? (If no → not done)
- Are all tests passing? (If no → not done)
- Is coverage above minimum thresholds? (If no → not done)
- Has it been reviewed and approved? (If no → not done)
- Is it merged to main? (If no → not done)
- Can it be deployed to production safely? (If no → not done)

If the answer to any question is "no," the work is not done.

### Partial Completion is Not Completion

- "90% done" = not done
- "Done except for tests" = not done
- "Done but needs review" = not done
- "Mostly working" = not done

Work is either done or in progress. There is no in-between.

---

## Consequences of Incomplete Work

### Technical Consequences

- Incomplete work creates technical debt
- Untested code leads to bugs in production
- Undocumented code is difficult to maintain
- Unreviewed code may contain errors or vulnerabilities

### Team Consequences

- Incomplete work blocks other developers
- Incomplete work increases context switching
- Incomplete work reduces trust in the codebase
- Incomplete work slows down development velocity

### User Consequences

- Incomplete features do not provide user value
- Incomplete bug fixes leave users affected by the bug
- Incomplete security measures expose user data to risk

---

## Continuous Improvement

### Retrospective Questions

After each feature or release, ask:
- Did we meet all completion criteria?
- Were any criteria unrealistic or unnecessary?
- Should we add new criteria based on issues encountered?
- How can we improve our definition of done?

### Evolving Definition of Done

The definition of done should evolve as the project matures:
- Add criteria when gaps are discovered
- Remove criteria that provide no value
- Adjust thresholds based on project needs
- Maintain team agreement on changes

---

## References

- Testing requirements: #[[file:08-testing.md]]
- Code review process: #[[file:05-team-workflow.md]]
- Coding standards: #[[file:04-coding-standards.md]]
- Security requirements: #[[file:07-security.md]]
- Multi-tenancy patterns: #[[file:02-domain-model.md]]
- AI platform patterns: #[[file:06-ai-platform.md]]

---

## Document Boundaries

This document defines completion criteria only. It establishes what "done" means for features, bug fixes, and releases.

**This document must never contain:**

- **Implementation details**: How to write code, specific algorithms, or coding patterns belong in other documents.
- **Testing implementation**: Specific test frameworks, test patterns, or test cases belong in #[[file:08-testing.md]].
- **Code review details**: Specific review criteria or processes belong in #[[file:05-team-workflow.md]].
- **Architecture**: System layers, component boundaries, or dependency rules belong in #[[file:03-system-architecture.md]].
- **Security policies**: Authentication, authorization, or secret management belong in #[[file:07-security.md]].

This document focuses exclusively on **completion criteria** (what must be true for work to be considered done, checklists for features/bugs/releases, and measuring completeness).

When questions arise about other topics, refer to the appropriate steering document.
