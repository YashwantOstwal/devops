# SonarQube release gate

SonarQube statically analyzes source code for bugs, vulnerabilities, and maintainability issues. It does not detect every bug or replace automated tests. A **quality gate** turns its findings into a pass/fail release decision.

On every push to `main`:

```text
Gitleaks → Maven tests + JaCoCo → SonarQube analysis + quality gate
         → Docker image published to GHCR → production AKS rollout
```

A test failure, missing Sonar configuration, scanner error, server outage, gate timeout (300 seconds), or failed quality gate blocks image publication and deployment. Existing production remains running. Fixing the issue and pushing again reruns the pipeline. Pull requests targeting `main` run Gitleaks and tests only and never publish images; the merged commit must pass analysis before release. This supports free SonarQube Community Build, which does not support PR/branch analysis. Other branches do not trigger this workflow.

## One-time setup

1. Use a persistent SonarQube Community Build/Server reachable from GitHub-hosted runners over HTTPS, or create a SonarQube Cloud project. A server at `localhost` on your laptop is **not** reachable by GitHub runners. A private server needs a suitably networked runner.
2. Create/import a project with `main` as its main branch. Keep the Java **Sonar way** quality profile active. For Cloud, disable Automatic Analysis and select CI-based analysis. Cloud eligibility and branch analysis depend on your plan.
3. Create and assign a custom quality gate. Include **overall code** conditions so existing bugs and first analyses cannot slip past a new-code-only baseline:

   | Experience mode | Fail condition on overall code |
   |---|---|
   | Standard Experience | Bugs > 0; Vulnerabilities > 0 |
   | Multi-Quality Rule (MQR) | Reliability rating worse than A; Security rating worse than A |

   Optionally add a coverage threshold after reviewing the baseline report; the bootstrap main method is not exercised by the current HTTP tests. Preserve built-in new-code conditions if cloning Sonar way. Metric labels vary by server version. Assign the gate to the project explicitly; creating it alone is not enough.
4. Generate a project analysis token. In GitHub → repository Settings → Secrets and variables → Actions, configure:

   | Kind | Name | Value |
   |---|---|---|
   | Secret | `SONAR_TOKEN` | Project analysis token; never commit it |
   | Variable | `SONAR_HOST_URL` | Server URL, or `https://sonarcloud.io` for EU Cloud |
   | Variable | `SONAR_PROJECT_KEY` | Exact project key |
   | Variable | `SONAR_ORGANIZATION` | Cloud organization key; omit for self-hosted SonarQube |

   This setup supports self-hosted SonarQube or EU Cloud. US Cloud requires the additional scanner parameter `sonar.region=us`.
5. Keep existing Azure secrets (`AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`) configured. The workflow targets resource group `my-devops-rg` and AKS cluster `my-aks-cluster`. Ensure AKS can pull the GHCR image and the `cicd-demo` namespace exists.
6. Push to `main`. Check **SonarQube analysis and required quality gate** in Actions and the matching project dashboard. Only a successful analysis job unlocks publication and deployment.

Do not add `continue-on-error`, skip analysis when the token is absent, or use `always()` on deployment. These would bypass the gate. Branch protection can additionally require tests before merging; it is separate from this mandatory release gate.

## Local verification

```bash
mvn -B -ntp clean verify
python3 -m unittest discover -s tests -v
```

Coverage appears at `target/site/jacoco/index.html`. SonarQube imports `target/site/jacoco/jacoco.xml`. Scanner and JaCoCo versions are pinned in `pom.xml`.

Set `SONAR_HOST_URL`, `SONAR_PROJECT_KEY`, and `SONAR_TOKEN` in your shell (use a secret manager or hidden input for the token), then run:

```bash
bash scripts/sonar-scan.sh
```

## Demonstrate a bug blocking deployment

Use a dedicated demo project/repository or local copy; do not intentionally break production. Configure the overall-code gate above first.

1. Scan the unchanged app and confirm a passing gate.
2. Temporarily add `src/main/java/com/example/cicd/QualityGateDemo.java`:

   ```java
   package com.example.cicd;

   public class QualityGateDemo {
       public int length() {
           String value = null;
           return value.length();
       }
   }
   ```

3. Run `mvn clean verify` and `bash scripts/sonar-scan.sh`. Tests still pass because the unused class is not called. SonarQube detects the null dereference (`java:S2259`); the overall-code gate fails and the scanner returns nonzero. On a demo GitHub repository using this workflow, the image and deployment jobs are **skipped**.
4. Remove the demo class, run `mvn clean verify`, and scan again. The bug disappears and the gate passes. A fixed push to `main` then publishes and deploys when the external services are configured.
5. Capture the SonarQube issue, failed workflow with skipped deployment, and successful fixed workflow for your teacher.

## Verification performed

- `mvn clean verify` passed with a clean Temurin Java 17 runtime: 3 application tests passed, the executable JAR was built, and JaCoCo XML/HTML reports were generated.
- Baseline line coverage is 75% (6 of 8 lines); the bootstrap main method is uncovered.
- All 6 Python gate-script tests passed, including missing configuration/coverage and scanner failure propagation. These use a stub scanner and do not claim to prove SonarQube bug detection.
- Workflow YAML, release dependencies, shell syntax, and `git diff --check` were checked.
- The real pinned Maven scanner was run against an unreachable local URL: it returned exit code 1, confirming server outages fail the scan step.
- A live SonarQube bug/fix scan and GitHub production rollout have **not** been verified. No SonarQube credentials/project are configured in GitHub. The local server attempt was blocked by disk space and Docker/systemd startup failures; temporary test containers were removed.

## References

- [SonarScanner for Maven](https://docs.sonarsource.com/sonarqube-server/analyzing-source-code/scanners/sonarscanner-for-maven)
- [Waiting for quality gates in CI](https://docs.sonarsource.com/sonarqube-community-build/analyzing-source-code/ci-integration/overview)
- [Understanding quality gates](https://docs.sonarsource.com/sonarqube-community-build/quality-standards-administration/managing-quality-gates/introduction-to-quality-gates)
