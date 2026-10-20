---
name: jenkins-pipeline-unit
description: Create, run, and debug Spock tests for Jenkinsfiles and shared libraries using JenkinsPipelineUnit. Use for step mocks, shell/file/credential behavior, Spock interactions and data tables, invocation assertions, test discovery failures, or debugging failing Pipeline unit tests.
---

# Jenkins Pipeline Unit

Test Pipeline orchestration with Spock and JenkinsPipelineUnit (JPU), not a running Jenkins controller. Use the project's existing build, test runner, source sets, and fixtures. Build provisioning and dependency upgrades are outside this skill; report missing prerequisites as blockers.

## Workflow

1. Find an existing spec, its fixture, and the project's focused test command. Run the nearest relevant test to establish the baseline. Confirm actual feature executions rather than a successful task with zero tests.
2. Identify the subject: scripted Jenkinsfile/`vars` script, declarative Jenkinsfile, or injected-script library class. When creating or changing a fixture or subject loader, read the relevant section of [fixtures and subjects](references/fixtures-and-subjects.md). Mock external boundaries rather than the function under test.
3. Enumerate each consumed boundary's signature and result shape. When adding or changing a mock, consult only the matching section of [mock recipes](references/mocking.md): signatures/returns, wrappers, shell, files, binding, credentials, or failures. Register mocks after `base.setUp()` and before loading code that consumes them. Use fail-closed shell mocks for commands relevant to the test.
4. Cover success, branch/skip, and failure paths with Spock `given/when/then`, interactions, and `where:` tables. When choosing or correcting an assertion, consult the matching section of [assertions](references/assertions.md): invocation counts/arguments/order, exceptions/status, snapshots, or Spock interactions. Each test must reach its intended branch and verify an observable effect, including forbidden work not occurring.
5. Run the focused spec, then the normal suite. For discovery problems, unexpected mocks, or failing conditions, use [execution and debugging](references/execution-and-debugging.md). Report commands, executed cases, results, and integration behavior still untested.

## Guardrails

- Match the installed JPU API; consult [source audit](references/sources.md) for inspected implementations and historical verification, not required dependency pins.
- Default mocks are permissive approximations. Shell success is the fallback; `writeFile` does not persist files; `error` sets failure but does not abort. Choose explicit behavior when those distinctions affect the test.
- `parallel` runs branches sequentially. Mock tests do not establish concurrency, sandbox acceptance, restart/resume safety, or actual plugin behavior; those require controller-backed integration tests.
