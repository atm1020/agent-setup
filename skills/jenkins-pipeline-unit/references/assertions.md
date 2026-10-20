# Invocation and outcome assertions

Use inside a Spock `Specification` with the composed `base`, `helper`, and `binding` from [fixtures and subjects](fixtures-and-subjects.md). Count and argument snippets assume the subject has already run. Inside Spock `then:`/`expect:`, ordinary Boolean expressions are conditions; explicit `assert` remains useful inside callback closures.

## Count, absence, and exact argument values

```groovy
assert helper.methodCallCount('archiveArtifacts') == 1
helper.verify('archiveArtifacts', 1) { call ->
    call.args[0].artifacts == 'dist/*.zip' && call.args[0].fingerprint == true
}
helper.verify('mail', 0)
```

`verify(name, times = 1, predicate = { true })` applies the predicate to **every** call with that name, then checks the **total** count. The predicate is not a filter. Return a Boolean expression or explicitly `true` after internal assertions; a closure ending in a successful `assert` may return null and fail verification.

To count only matching calls, filter explicitly:

```groovy
def shellCalls = helper.callStack.findAll { it.methodName == 'sh' }
def commands = shellCalls.collect { call ->
    def arg = call.args[0]
    arg instanceof Map ? arg.script.toString() : arg.toString()
}
assert commands.count { it == './deploy.sh --target staging' } == 1
assert !commands.any { it.contains('--target production') }
```

`MethodCall` exposes `methodName`, `args`, `target`, and `stackDepth`. String and Map overloads both appear under the same method name. Loading and running scripts also creates entries, so avoid asserting the total stack size when you mean one step's count.

## Order

```groovy
assert commands == ['git rev-parse HEAD', './build.sh', './deploy.sh --target staging']
// Relative order when unrelated steps may intervene:
assert commands.indexOf('./build.sh') >= 0
assert commands.indexOf('./deploy.sh --target staging') > commands.indexOf('./build.sh')
```

Sequential recording proves observed mock order, not runtime order between real parallel branches. Filter by `target` as well if multiple loaded scripts emit indistinguishable calls.

## Arguments: snapshots versus live references

The helper normally clones Cloneable arguments; non-Cloneable values become strings. Cloning is not a guaranteed deep snapshot of arbitrary nested structures. Inspect the recorded type before doing deep assertions. For complex objects, prefer assertions or explicit snapshots inside the mock callback.

```groovy
// Set BEFORE execution only when you deliberately need original object identity/type.
helper.cloneArgsOnMethodCallRegistration = false
```

This records live references, so later mutations can change what the test sees. Use `callArgsToString(call)` (static utility on `MethodCall`) for diagnostic string matching, not as the first choice for structured equality.

`clearCallStack()` clears recorded calls between phases, not shell mocks or callback state. Prefer fresh fixtures per test; clearing is useful to exclude setup calls before a specific action.

## Exceptions and build status are separate contracts

```groovy
def 'rejected deployment aborts before archiving'() {
    given:
    helper.registerAllowedMethod('error', [String]) { String message ->
        base.updateBuildStatus('FAILURE')
        throw new IllegalStateException(message)
    }

    when:
    base.runInlineScript("error 'deployment rejected'; archiveArtifacts artifacts: 'dist/*'")

    then:
    def failure = thrown(IllegalStateException)
    failure.message == 'deployment rejected'
    base.assertJobStatusFailure()
    helper.verify('archiveArtifacts', 0)
}
```

Status helpers are `assertJobStatusSuccess`, `assertJobStatusFailure`, `assertJobStatusUnstable`, and `assertJobStatusAborted`. They inspect `currentBuild.result`. A thrown exception alone need not update it; choose a mock or subject path that establishes the status you assert. For a caught exception, verify the recovery step and final status rather than expecting a throw from the whole script.

## Diagnostics and snapshot regression

```groovy
base.printCallStack()
// In then: verify the recorded behavior with a Spock condition.
helper.callStack.any { it.methodName == 'archiveArtifacts' }
```

For broad orchestration regression tests, compose a `BaseRegressionTest` fixture instead of `BasePipelineTest` and call `base.testNonRegression('scenario-name')` after execution. Generate/update the reference file intentionally with `-Dpipeline.stack.write=true`, inspect the diff, then rerun in comparison mode. Commit reviewed snapshots; never silently regenerate them to make failing CI green. Precise assertions are preferable for critical branching, secrets, and command arguments.

## Spock interactions and data tables

Use Spock `@Unroll` and `where:` tables to cover parameter/environment combinations. For each row, assert both the expected invocation and absence of forbidden work. For example, a feature can register a shell result using an `exitCode` table column, execute the real subject, and compare its returned status and `currentBuild.result` with expected columns. Keep branch-specific invocation assertions in the same `then:` block.

Prefer a typed Spock collaborator behind a real registered closure:

```groovy
// Declare at top level in the spec file:
interface ReleaseApi { Map request(Map args) }

// Inside a feature:
given:
def api = Mock(ReleaseApi)
helper.registerAllowedMethod('httpRequest', [Map]) { Map a -> api.request(a) }

when:
def script = base.loadInlineScript("httpRequest(url: 'https://example.invalid/releases')")
def response = base.runScript(script)

then:
1 * api.request({ Map a -> a.url.endsWith('/releases') }) >> [status: 201, content: 'ok']
0 * api._
response.status == 201
```

Put interaction cardinality and stub return together in `then:`. Splitting the same mocked invocation into a `given:` stub and `then:` count can cause the verification interaction to take precedence and return a default null. `0 * api._` closes this collaborator's contract without rejecting unrelated JPU activity.

If using Spock interactions against a mocked Closure, confirm callback argument nesting against the installed JPU version. The linked historical example's `args[0][0]` workaround describes JPU 1.1, not a universal API. Typed real closures plus call-stack assertions avoid that dependency.
