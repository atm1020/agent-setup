# Test fixtures, scripts, and shared libraries

Use the project's existing Spock/JenkinsPipelineUnit build and test source set. Reuse its fixture where possible; the examples below show test-level lifecycle and subject loading, not build provisioning.

## Compose shared JPU support into a Spock specification

Reuse the project's JPU fixture, or compose `BasePipelineTest` as below. The spec extends `Specification`, since Groovy does not support inheriting both base classes.

```groovy
import com.lesfurets.jenkins.unit.BasePipelineTest
import com.lesfurets.jenkins.unit.PipelineTestHelper
import spock.lang.Specification

class BuildSpec extends Specification {
    BasePipelineTest base
    PipelineTestHelper helper
    Binding binding

    def setup() {
        base = new BasePipelineTest() {}
        base.scriptRoots = ['.', 'vars', 'src/test/resources'] as String[]
        base.setUp()
        helper = base.helper
        binding = base.binding
        helper.addShMock { String command ->
            throw new IllegalStateException("Unexpected sh: ${command}")
        }
    }

    def 'build invokes make'() {
        given:
        helper.addShMock('make', '', 0)

        when:
        base.runScript('Jenkinsfile') // Real subject expected to invoke make.

        then:
        helper.methodCallCount('sh') == 1
        helper.callStack.find { it.methodName == 'sh' }.args[0] == 'make'
        base.assertJobStatusSuccess()
    }
}
```

Use `setup()`, `given/when/then`, `thrown()`, interactions, and `where:` tables throughout. A fresh composed base per feature/iteration prevents shell-handler, binding, and callback leakage. Avoid `@Shared` JPU fixtures. Configure loader paths before `base.setUp()`; register boundary mocks afterward. Keep that initialized helper: replacing it after setup disconnects registrations, binding, and loader configuration.

The example installs a fail-closed `sh` fallback before each feature adds allowed commands. Do the same for `bat` when relevant. Keep scenario-specific returns, Spock mocks, and expectations in each feature. For abort behavior, register an explicitly throwing `error` callback as shown in [mock recipes](mocking.md).

Base searches `src/main/jenkins` and project root by default. Set `baseScriptRoot`/`scriptRoots` before initialization for another layout. Prefix inherited JPU convenience methods with `base.`; a Spock specification does not inherit them.

## Load the actual subject

```groovy
base.runScript('Jenkinsfile')                    // Compile and execute top-level code.
def job = base.loadScript('jobs/build.groovy')   // Compile/load only.
job.execute()                                   // Only if job declares execute().
def step = base.loadScript('vars/release.groovy')
step.call([target: 'staging'])                   // Exercise the real global step.
```

`loadScript` and `loadInlineScript` compile/load without executing top-level code or inventing an `execute()` method. For scalar/map inline results, use `base.runScript(base.loadInlineScript(code))`: the inspected `runInlineScript` implementation casts results to `Script`.

Mock other global steps using their actual signatures. To exercise `@Library`, imported `src` classes, globals, and resources together, register a real local library rather than replacing the code under test.

## Register the current library without fetching Git

```groovy
import static com.lesfurets.jenkins.unit.global.lib.LibraryConfiguration.library
import static com.lesfurets.jenkins.unit.global.lib.ProjectSource.projectSource

// In setup(), after base.setUp(), before loading the consuming pipeline:
helper.registerSharedLibrary(library()
    .name('commons')
    .defaultVersion('test')
    .allowOverride(false)
    .implicit(false)
    .targetPath('unused')
    .retriever(projectSource())
    .build())
base.runScript('src/test/resources/usesCommons.Jenkinsfile')
// Fixture: @Library('commons') _
//          release(target: 'staging')
```

`projectSource()` uses the local working directory containing `src/`, `vars/`, and `resources/`, regardless of requested version. Keep version overrides disabled; use versioned local fixtures when versions matter. Other retrievers:

- `LocalSource.localSource('/fixture/root')` expects `/fixture/root/commons@test` for this name/version. Useful for multiple pre-staged library versions.
- `GitSource.gitSource(url)` fetches to the configured target. Prefer local fixtures for deterministic, offline unit tests.

Dynamic `library` loading is partial. Inspect the installed version's default String/Map callbacks before replacing them: historical examples manually constructed `LibClassLoader`, whereas current base code already registers loader callbacks.

If custom-class arguments to `vars` methods fail because a class was loaded twice, investigate classloader identity. `helper.libLoader.preloadLibraryClasses = false` is an upstream workaround, not a default; it can break library classes that depend on injected globals such as `env`.

## Inject script context into `src` classes

Keep `vars` entry points thin and pass the pipeline context into classes:

```groovy
// src/org/example/Release.groovy
package org.example
class Release implements Serializable {
    Object script
    String revision() {
        script.sh(script: 'git rev-parse HEAD', returnStdout: true).trim()
    }
}
```

A Spock feature exercises the real class with an intercepted script:

```groovy
def 'revision trims command output'() {
    given:
    helper.addShMock('git rev-parse HEAD', 'abc123\n', 0)
    def script = base.loadInlineScript('return this')
    def subject = new org.example.Release(script: script)

    expect:
    subject.revision() == 'abc123'
}
```

Ensure the library `src` directory is on the test classpath through existing source-set conventions, or load through the registered library. Test pure classes with plain Spock when they do not use Pipeline steps.

## Declarative, parallel, Docker, and specialized helpers

- For declarative DSL, compose `base = new com.lesfurets.jenkins.unit.declarative.DeclarativePipelineTest() {}` instead. The surrounding test still extends Spock `Specification`. Verify critical `when`/`post`/agent semantics against the selected version. Prefer this to copying historical handwritten declarative emulators.
- Built-in `parallel(Map)` runs branches sequentially, excludes the `failFast` entry, collects exceptions, marks failure, and throws an aggregate error. It does not reproduce scheduling or fail-fast cancellation.
- Bound `docker` is a `DockerMock`: `image`, `build`, `inside`, `withRun`, `withRegistry`, `withServer`, and `withTool` model calls/bodies without containers. Images support pull/push/tag/run; containers have mock id/port/stop. Assert calls or inject a test-owned fake for richer behavior. No daemon, filesystem, or networking is exercised.
- `load` and `parallel` have helper-owned interceptors. For fundamental loader customization, subclass `PipelineTestHelper`, supply it before base initialization, and test the adapter; callback replacement alone is not a full loader model.
- `BasePipelineTestCPS` is experimental and uses different serialization from Jenkins. Ordinary JPU tests cannot certify CPS compatibility.

Run the focused spec with the project's wrapper, for example `./gradlew test --tests '*BuildSpec'`, then its normal suite. Add no controller, network, shell-command, or Docker dependency to mock-only tests.
