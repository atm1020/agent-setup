# Source audit and verification

This is an authored skill, not a vendored upstream skill. Recipes were checked against source and tests rather than copied as an upstream skill bundle.

## Inspected repositories

| Repository | Commit | What was inspected |
|---|---|---|
| [jenkinsci/JenkinsPipelineUnit](https://github.com/jenkinsci/JenkinsPipelineUnit) | `9bb21a1ef14aa5f421231e2ad1c80117a39a25f9` | README, build metadata, step callbacks, shell matching/execution, call recording/verification, Docker mock, shared-library APIs, tests |
| [macg33zr/pipelineUnit](https://github.com/macg33zr/pipelineUnit) | `0dcd54f46e2733c141da0ce6fb5158f010fee645` | Spock base fixture, declarative emulator, Jenkinsfile spec with data tables and Closure interactions |
The macg33zr example is linked from the framework README. It is an independent Spock example, not an authoritative API definition. Its spec explicitly describes JPU 1.1's nested Closure argument workaround. Its data-table/interaction patterns are useful, but its custom declarative emulator is historical.

## Primary implementation pointers

Paths below resolve under the pinned [framework tree](https://github.com/jenkinsci/JenkinsPipelineUnit/tree/9bb21a1ef14aa5f421231e2ad1c80117a39a25f9).

- `src/main/groovy/com/lesfurets/jenkins/unit/BasePipelineTest.groovy`: lifecycle, built-in step overloads, `error`, `retry`, `withEnv`, credentials interception, binding defaults, status helpers, script loading/running.
- `src/main/groovy/com/lesfurets/jenkins/unit/PipelineTestHelper.groovy`: `registerAllowedMethod` overloads, callback dispatch, null-body fallback, `MockScriptHandler` constructors/validation, `addShMock`/`addBatMock` overloads, file defaults, `verify`, cloning, `parallel`, library registration, inline script return type.
- `src/main/groovy/com/lesfurets/jenkins/unit/MethodCall.groovy`: invocation fields and string formatting.
- `src/main/groovy/com/lesfurets/jenkins/unit/MethodSignature.groovy`: signature construction and compatible-type matching.
- `src/main/groovy/com/lesfurets/jenkins/unit/DockerMock.groovy`: supported image/container methods and placeholder values.
- `src/main/groovy/com/lesfurets/jenkins/unit/global/lib/`: `LibraryConfiguration`, `ProjectSource`, `LocalSource`, `GitSource`, loader implementations.
- `src/test/groovy/com/lesfurets/jenkins/unit/`: `VerifyTest`, `PipelineTestHelperTest`, `BasePipelineTestTest`, `DockerMockTest`, and declarative tests.
- `build.gradle`, `gradle.properties`, `README.md`: dependency/runtime constraints and examples. The inspected version property is 1.32; README's 1.9 dependency example is stale relative to that tree. No claim is made that HEAD equals a published release.

## Executed verification

In a temporary upstream checkout, outside this repository and generated tool folders:

1. Ran upstream `VerifyTest` successfully.
2. Used Spock 1.3-groovy-2.4 with the checkout's existing test runner.
3. Exercised scratch Spock features for shell output/status, regex callbacks, retry, typed interactions, stateful files, and abort behavior. Those standalone example files are no longer distributed by this skill.
4. Ran `./gradlew test --tests PipelineMockingSpec --console plain`: **8 cases passed** (seven features, including two exit-status table iterations), using Java 21 and upstream's Groovy 2.4.21.

Execution exposed two implementation details worth preserving:

- Shell callback validation rejects GString stdout even though it looks like a string; use `.toString()` for interpolation.
- The inspected helper declares `runInlineScript` as returning `Script`, causing cast failures for scalar/map script results. `base.runScript(base.loadInlineScript(code))` returns the actual result safely.

A separate historical scratch run used `gradlew test --tests '*PipelineMockingSpec' check --console plain` with Gradle 9.8.1 and Java 21. All **8 cases passed** against published JPU **1.31**, Groovy **2.4.21**, and Spock **1.3-groovy-2.4**, using `useJUnit()` for Spock 1.x discovery.

The credential-scope regression in [mock recipes](mocking.md#8-credentials-and-scoped-fake-values) was also extracted into a scratch Spock spec against the pinned checkout. All four combinations of absent/pre-existing values and successful/throwing nested `withEnv` bodies failed with the old cleanup and passed after re-reading the binding's `env` map in `finally`. The passing run used `./gradlew -I /tmp/credential-review-junit.gradle test --tests CredentialScopeReviewSpec --console plain`; the temporary init script selected `useJUnit()` after project evaluation for Spock 1.3. The checkout's JUnit Platform/Vintage runner failed to report unrolled features correctly, so it was not used for the final verification.

The entire upstream suite and every reference snippet were not executed. These historical runs are provenance, not required toolchain versions or verification of every current snippet. On upgrades, run the project's specs and inspect changed callbacks before assuming recipes are unchanged; mock tests do not establish real controller/plugin behavior.
