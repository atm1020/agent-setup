# Execute and debug Pipeline specs

## Focus the run

Use the project's documented command and wrapper. For an existing Gradle test task, these are useful options; substitute the actual task and spec name:

```bash
./gradlew test --tests '*BuildSpec' --console plain
./gradlew test --tests '*BuildSpec' --rerun-tasks --stacktrace --info --console plain
```

The first runs a focused spec. The second forces execution instead of relying on up-to-date results and adds task/exception diagnostics. Use a narrower feature filter only after confirming how the installed Spock/Gradle versions expose feature and data-iteration names.

Inspect the executed test count and reports, normally `build/reports/tests/<task>/index.html` and `build/test-results/<task>/`. An up-to-date task, `NO-SOURCE`, or zero discovered tests is not a fresh passing test run. After the focused spec passes, run the project's normal suite.

## Failure triage

| Symptom | Inspect next |
|---|---|
| No tests found | Spec package/name filter, actual test task, source-set location, and existing runner discovery. Compare with a known working spec. Report missing infrastructure rather than provisioning a build. |
| `MissingMethodException` | Actual argument types and overload: named arguments are a `Map`, trailing bodies are separate `Closure` arguments. Register before the consuming script loads. |
| Unexpected shell command | Exact whitespace/newlines and flags; regex uses whole-command matching. Keep the rejecting fallback first because the last matching shell handler wins. |
| Unexpected null from a Spock mock | Put cardinality and return together in `then:`; a verification interaction can override a separate stub. Check callback return shape. |
| Script method never runs, or inline result throws a cast error | Check the loading/execution distinction and inline-result workaround in [Load the actual subject](fixtures-and-subjects.md#load-the-actual-subject). |
| Test fails only after another feature | Check per-feature lifecycle in [fixture setup](fixtures-and-subjects.md#compose-shared-jpu-support-into-a-spock-specification), including bindings, shell handlers, and captured state. |
| Status and exception expectations disagree | They are separate contracts. Check whether the subject/mock updates `currentBuild` and whether `error` actually throws. |
| Recorded arguments look wrong | JPU may clone/stringify arguments. Capture deliberate snapshots inside the callback; disabling cloning records mutable live references. |
| Library type appears incompatible with itself | Inspect duplicate class loading and library registration; see [fixtures and subjects](fixtures-and-subjects.md). |

## Inspect execution

Print the recorded calls after execution, including when the subject throws:

```groovy
when:
try {
    base.runScript('Jenkinsfile')
} finally {
    base.printCallStack()
}
```

Use Spock's condition diff and exception stack first, then narrow `helper.callStack` by `methodName`, arguments, and `target`. Add temporary callback assertions to establish which branch ran and what data crossed the boundary. Avoid printing credentials or sensitive environment values.

For a debugger, an existing Gradle `Test` task supports:

```bash
./gradlew test --tests '*BuildSpec' --rerun-tasks --debug-jvm
```

It normally suspends the test JVM for debugger attachment on port 5005 unless the project customizes debugging. Break in the spec, callback, or loaded Groovy subject; this inspects the local mock test, not a Jenkins controller or real CPS execution.

Remove temporary tracing before finishing. Preserve the reproduction as a focused failing-then-passing spec and report the command, executed cases, root cause, and any runtime contract left untested.
