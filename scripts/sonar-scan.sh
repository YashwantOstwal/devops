#!/usr/bin/env bash
set -euo pipefail

# Fail closed: absent configuration must never silently authorize a release.
for variable in SONAR_TOKEN SONAR_HOST_URL SONAR_PROJECT_KEY; do
  if [[ -z "${!variable:-}" ]]; then
    echo "::error::Missing $variable. Follow SONARQUBE.md before deploying." >&2
    exit 1
  fi
done

if [[ ! -s target/site/jacoco/jacoco.xml ]]; then
  echo '::error::Coverage report missing. Run mvn clean verify before analysis.' >&2
  exit 1
fi

arguments=(
  "-Dsonar.host.url=$SONAR_HOST_URL"
  "-Dsonar.projectKey=$SONAR_PROJECT_KEY"
  '-Dsonar.qualitygate.wait=true'
  '-Dsonar.qualitygate.timeout=300'
)
if [[ -n "${SONAR_ORGANIZATION:-}" ]]; then
  arguments+=("-Dsonar.organization=$SONAR_ORGANIZATION")
fi

# SONAR_TOKEN is consumed from the environment, not exposed in CLI arguments.
exec mvn -B -ntp org.sonarsource.scanner.maven:sonar-maven-plugin:sonar "${arguments[@]}"
