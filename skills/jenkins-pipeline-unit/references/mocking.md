# Mock recipes

Snippets run inside a Spock `Specification` composing a configured JPU fixture named `base`, with `helper = base.helper` and `binding = base.binding`; see [fixtures and subjects](fixtures-and-subjects.md). Register mocks after `base.setUp()`. These are current-source behaviors; see [the audit](sources.md) before applying them to older versions.

## 1. Step signatures, constant returns, callbacks, and side effects

Named arguments are one `Map`; a trailing body is a separate `Closure`. Register the overload actually called. An unrecognized method/signature raises `MissingMethodException`.

```groovy
// No arguments; callback return becomes step return.
helper.registerAllowedMethod('isUnix', []) { true }
// Scalar and named-argument overloads are separate registrations.
helper.registerAllowedMethod('tool', [String]) { String name -> "/tools/${name}" }
helper.registerAllowedMethod('tool', [Map]) { Map a -> "/tools/${a.name}" }
helper.registerAllowedMethod('myStep', [String, Integer]) { String name, Integer n ->
    [name: name, copies: n]
}
// Allow/log a side-effect-only step.
helper.registerAllowedMethod('cleanWs')
helper.registerAllowedMethod('archiveArtifacts', [Map]) { Map a ->
    assert a.artifacts == 'dist/*.zip'
    assert a.fingerprint
    null
}
```

Use `[Integer]` for a Groovy integer argument; check actual types if a primitive/boxed or custom-class signature fails. Registering the same signature replaces its callback. Avoid overlapping broad signatures such as `[Object]` and `[String]`: lookup uses the first compatible entry, not “most specific wins”. This differs from shell handler precedence.

Public registration forms:

- `registerAllowedMethod(String name, Closure callback = null)` — zero-argument signature.
- `registerAllowedMethod(String name, List<Class> types, Closure callback = null)`.
- `registerAllowedMethod(MethodSignature signature, Closure callback = null)`.
- `registerAllowedMethod(MethodSignature signature, java.util.function.Function callback)` — return value.
- `registerAllowedMethod(MethodSignature signature, java.util.function.Consumer callback)` — side effect.

Construct signatures with `MethodSignature.method('step', Map.class)` when using the Java functional overloads. Prefer closures in Groovy.

A null/omitted callback is **not** a reliable way to suppress a body. For an allowed missing method, the helper executes closure arguments (also closures in map keys/values) and returns the last closure result. To intentionally skip a wrapper body, supply an explicit callback that returns null without calling it.

## 2. Structured return data and object-like responses

Return exactly the fields/types the subject reads; mocks do not install the plugin.

```groovy
helper.registerAllowedMethod('checkout', [Map]) { Map a ->
    [GIT_COMMIT: 'abc123', GIT_BRANCH: 'origin/main']
}
helper.registerAllowedMethod('readJSON', [Map]) { Map a ->
    assert a.file == 'release.json'
    [version: '2.4.0', targets: ['linux', 'windows']]
}
helper.registerAllowedMethod('readYaml', [Map]) { Map a ->
    [deployment: [replicas: 3], enabled: true]
}
helper.registerAllowedMethod('httpRequest', [Map]) { Map a ->
    assert a.url == 'https://example.invalid/releases'
    [status: 201, content: '{"id":42}', headers: [Location: '/releases/42']]
}
helper.registerAllowedMethod('build', [Map]) { Map a ->
    [number: 42, result: 'SUCCESS', absoluteUrl: 'https://jenkins.invalid/job/downstream/42/']
}
helper.registerAllowedMethod('input', [Map]) { Map a -> 'approved' }
helper.registerAllowedMethod('libraryResource', [String]) { String path ->
    assert path == 'templates/config.json'
    '{"enabled":true}'
}
```

Map property access works for `response.status`. If production calls `response.getStatus()`, return an object implementing that method (for example `new Expando(getStatus: { 201 })`), or the real response type available on the test classpath. Returning a parsed map from `readJSON`/`readYaml` tests consumers, not parsing. Exercise parsing separately if it is the contract.

## 3. Dynamic results, sequential outcomes, and exceptions

```groovy
def replies = [[state: 'PENDING'], [state: 'READY']].iterator()
helper.registerAllowedMethod('pollDeployment', [String]) { String id ->
    assert id == 'deploy-42'
    assert replies.hasNext(): 'Unexpected extra poll'
    replies.next()
}
helper.registerAllowedMethod('publishArtifact', [Map]) { Map a ->
    throw new IllegalStateException('registry unavailable')
}
```

Track invocations in a test-owned list when you need original complex arguments or state at call time. Mutable captured data must be copied intentionally if later mutations matter.

## 4. Body/wrapper steps

```groovy
def locks = []
helper.registerAllowedMethod('lock', [Map, Closure]) { Map a, Closure body ->
    locks << a.resource
    try {
        return helper.callClosure(body)
    } finally {
        locks.remove(locks.size() - 1)
    }
}
helper.registerAllowedMethod('timestamps', [Closure]) { Closure body ->
    helper.callClosure(body)
}
```

Execute the body exactly as often as the modeled contract requires and propagate its return/exception. A wrapper mock is not a timeout, lock, workspace, or container implementation. Existing `retry` retries exceptions; `waitUntil`'s default allowed-body execution is not a polling engine. Model bounded polling explicitly when needed.

## 5. Shell: every helper registration option

`sh` and `bat` have separate handler lists. The default String/Map step callbacks call `helper.runSh`/`runBat`; preserve them when using the helpers below. `powershell`/`pwsh` require explicit step registrations; there are no equivalent dedicated helper methods in the inspected source.

| Registration | Effect |
|---|---|
| `addShMock(String stdout, int exitValue)` | Static match-all shell result |
| `addShMock(String command, String stdout, int exitValue)` | Exact command |
| `addShMock(Pattern pattern, String stdout, int exitValue)` | Whole-command regex |
| `addShMock(String command, Closure callback)` | Exact command, dynamic result |
| `addShMock(Pattern pattern, Closure callback)` | Regex, dynamic result/captures |
| `addShMock(Closure callback)` | Dynamic match-all |
| `addBatMock(String command, String stdout, int exitValue)` | Exact Windows command |
| `addBatMock(Pattern pattern, String stdout, int exitValue)` | Windows regex |
| `addBatMock(String command, Closure callback)` | Exact Windows callback |
| `addBatMock(Pattern pattern, Closure callback)` | Windows regex callback |
| `addBatMock(Closure callback)` | Windows match-all callback |

There is no two-argument `addBatMock(stdout, exitValue)` overload in this source; use a match-all callback instead.

```groovy
// Add fallback FIRST, then permitted commands. Never create a fresh helper here.
helper.addShMock { String cmd ->
    throw new IllegalStateException("Unexpected sh: ${cmd}")
}
helper.addShMock('git rev-parse HEAD', 'abc123\n', 0)
helper.addShMock('./verify.sh', '', 2)
helper.addShMock(~/\.\/deploy\.sh --target (\w+)/) { String command, String target ->
    assert target in ['staging', 'production']
    [stdout: "deployed:${target}\n".toString(), exitValue: 0]
}
helper.addBatMock('ver', 'Windows\r\n', 0)
helper.addBatMock { String cmd -> [stdout: '', exitValue: 0] }
// Above bat catch-all was added LAST, so it masks the earlier 'ver' handler.
```

Callbacks return `[stdout: String, exitValue: int]`. Validation requires a real `String` (convert interpolated GStrings with `.toString()`) and an `Integer` exit code. Regex callbacks receive full match followed by **each** capture group; match callback arity accordingly. Regex matching uses `matches()`, not substring search: use `(?s).*...*` as appropriate for multiline commands. Exact matching includes whitespace/newlines/arguments. The **last matching handler wins**, handlers are reusable (not consumed), and unmatched commands otherwise get the default `['', 0]` success.

| Pipeline invocation | Successful mock return | Nonzero `exitValue` |
|---|---|---|
| `sh 'command'` / `sh(script: 'command')` | `null` | Throws exception |
| `sh(script: 'command', returnStdout: true)` | Exact stdout, including newline | Throws exception |
| `sh(script: 'command', returnStatus: true)` | Integer zero | Returns integer exit code |

`returnStatus` and `returnStdout` together throw `IllegalArgumentException`. The same semantics apply to `bat`. A shell exception does not automatically establish the same `currentBuild` state as Jenkins: assert the exception and separately assert status when the subject/mock updates it.

For `pwsh` or other steps, model flags explicitly, or delegate to `helper.runSh(a)` if intentionally reusing the sh mock list. Generic `registerAllowedMethod('sh', [Map]) { ... }` **bypasses** shell handlers and must implement stdout/status/failure behavior itself.

## 6. Files, existence, and stateful writes

```groovy
helper.addFileExistsMock('release.json', true)
helper.addReadFileMock('release.json', '{"version":"2.4.0"}')
// Supports readFile('release.json') and readFile(file: 'release.json', encoding: 'UTF-8').
```

Unknown files default to `false` for `fileExists` and `''` for `readFile`; these helpers do not read disk. `writeFile` is an allowed no-op by default. Model round trips explicitly:

```groovy
def files = [:]
helper.registerAllowedMethod('writeFile', [Map]) { Map a -> files[a.file] = a.text; null }
helper.registerAllowedMethod('fileExists', [String]) { String path -> files.containsKey(path) }
helper.registerAllowedMethod('readFile', [Map]) { Map a ->
    assert files.containsKey(a.file): "Missing fixture: ${a.file}"
    files[a.file]
}
helper.registerAllowedMethod('readFile', [String]) { String path ->
    assert files.containsKey(path): "Missing fixture: ${path}"
    files[path]
}
```

Register `[Map]` for `fileExists` too if the subject uses that form. Neither model simulates workspace paths, directory changes, encoding, or external shell filesystem effects automatically.

## 7. Binding variables, parameters, environment, and build objects

```groovy
base.addParam('DEPLOY', false)                    // Boolean, not the string 'false'.
base.addParam('DEPLOY', true, true)               // Explicitly overwrite an existing value.
base.addEnvVar('BRANCH_NAME', 'main')
base.addPreviousBuild('UNSTABLE')
binding.setVariable('scm', [branches: [[name: '*/main']]])
binding.getVariable('currentBuild').changeSets = [[items: [[msg: 'fix build']]]]
binding.setVariable('releaseService', new Expando(lookup: { String id -> [id: id] }))
```

`params` is immutable; use `addParam`, not direct map mutation. `env` and `currentBuild` are simple maps; add the exact nested fields the subject reads (`rawBuild`, causes, previous build, etc.). `updateBuildStatus('FAILURE')` updates both `result` and `currentResult`; direct assignment does not synchronize them. Fresh base setup supplies a Docker mock, empty env/scm/params, and a mock current build.

Default `withEnv(List, Closure)` temporarily applies entries to `env` and restores it. Prefer that built-in behavior unless the test requires different semantics.

## 8. Credentials and scoped fake values

Built-in `string` and `usernamePassword` bindings supply placeholder values based on variable names. They do not retrieve secrets. `addCredential(key, value)` populates a separate `credentials` binding map; it is **not** a general credentials-store integration for scripted `withCredentials`.

For a test that depends on a particular fake token, override both descriptor handling and wrapper behavior:

```groovy
helper.registerAllowedMethod('string', [Map]) { Map a -> a }
helper.registerAllowedMethod('withCredentials', [List, Closure]) { List specs, Closure body ->
    def env = binding.getVariable('env')
    def variables = binding.variables
    def saved = [:]
    specs.each { Map spec ->
        assert spec.credentialsId == 'release-token'
        String key = spec.variable
        saved[key] = [envPresent: env.containsKey(key), envValue: env[key],
                      present: variables.containsKey(key), value: variables[key]]
        env[key] = 'fake-token'
        binding.setVariable(key, 'fake-token')
    }
    try {
        return helper.callClosure(body)
    } finally {
        // withEnv may replace the binding's map while the body runs.
        env = binding.getVariable('env')
        saved.each { key, old ->
            if (old.envPresent) env[key] = old.envValue
            else env.remove(key)
            if (old.present) binding.setVariable(key, old.value)
            else variables.remove(key)
        }
    }
}
// Subject: withCredentials([string(credentialsId: 'release-token', variable: 'TOKEN')]) { ... }
```

With the registrations above in `setup()`, this regression feature checks cleanup after nested `withEnv`, both on return and on exception, with absent and pre-existing values:

```groovy
@spock.lang.Unroll
def 'credentials restore scope after nested withEnv (present=#present, failure=#bodyFails)'() {
    given:
    if (present) {
        binding.getVariable('env').TOKEN = 'previous-env'
        binding.setVariable('TOKEN', 'previous-binding')
    }
    binding.setVariable('bodyFails', bodyFails)
    Exception failure = null

    when:
    try {
        base.runScript(base.loadInlineScript('''
            withCredentials([string(credentialsId: 'release-token', variable: 'TOKEN')]) {
                withEnv(['OTHER=value']) {
                    assert env.TOKEN == 'fake-token'
                    assert TOKEN == 'fake-token'
                    if (bodyFails) throw new IllegalStateException('body failed')
                }
            }
        '''))
    } catch (IllegalStateException error) {
        failure = error
    }

    then:
    (failure?.message) == (bodyFails ? 'body failed' : null)
    binding.getVariable('env').containsKey('TOKEN') == present
    binding.getVariable('env').TOKEN == (present ? 'previous-env' : null)
    binding.hasVariable('TOKEN') == present
    binding.variables.TOKEN == (present ? 'previous-binding' : null)

    where:
    present | bodyFails
    false   | false
    true    | false
    false   | true
    true    | true
}
```

This recipe intentionally supports secret-text descriptors only. For username/password or file credentials, implement and validate those descriptor shapes and restore every injected variable in `finally`. Use fake values only; unit tests cannot establish log masking or secure credential storage.

## 9. Abort and failure fidelity

Default `error(String)` calls `updateBuildStatus('FAILURE')` but does **not** throw. For abort/catch/retry tests:

```groovy
helper.registerAllowedMethod('error', [String]) { String message ->
    base.updateBuildStatus('FAILURE')
    throw new IllegalStateException(message)
}
```

Use an available Jenkins exception type only when the subject distinguishes it; a generic exception is sufficient for generic error paths. Built-in `catchError`/`warnError` simulate catching and status changes, not every plugin option. Verify the installed implementation if relying on interruption or stage-result behavior.
