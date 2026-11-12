# CI/CD Demo for a Java Web Application

This project demonstrates an end-to-end DevOps workflow for a Java web application using Maven, Docker, Kubernetes, GitHub Actions, and Ansible. The application exposes a simple REST API and health endpoint, and the pipeline automatically builds, tests, packages, and deploys the service whenever changes are pushed to the repository.

## Project architecture

```mermaid
flowchart LR
    A[Developer pushes code] --> B[GitHub Repository]
    B --> C[GitHub Actions workflow]
    C --> D[Maven: build + test]
    D --> Q[SonarQube quality gate]
    Q --> E[Docker build + tag]
    E --> F[Push image to GHCR]
    F --> G[Kubernetes deployment]
    G --> H[LoadBalancer service]
    H --> I[Browser / HTTP endpoint]
```

## Tech stack

- Java 17
- Maven
- Spring Boot 3.3.4
- Docker
- Kubernetes
- GitHub Actions
- Ansible
- Azure Kubernetes Service (AKS) deployment target

## Local development

### Prerequisites

- Java 17+
- Maven 3.9+
- Docker Desktop or a Docker engine
- kubectl (for Kubernetes validation)

### Run the app locally

```bash
mvn clean test
mvn spring-boot:run
```

Then open the following endpoints in the browser:

- http://localhost:8080/
- http://localhost:8080/health
- http://localhost:8080/api/version

### Build the Docker image locally

```bash
docker build -t cicd-demo:local .
docker run --rm -p 8080:8080 cicd-demo:local
```

## CI/CD pipeline overview

The GitHub Actions workflow performs the following stages:

1. Check out the full repository history.
2. Scan the repository for leaked secrets with Gitleaks.
3. Check out the source code.
4. Install Java 17 and Maven dependencies.
5. Run the automated test suite.
6. Package the application into a JAR file.
7. Require a passing SonarQube quality gate before building the Docker image.
8. Push the image to GitHub Container Registry.
9. Authenticate to Azure.
10. Update the AKS deployment with the new image.
11. Wait for the rollout to finish.

The deployment files are in the `k8s/` folder.

### Required SonarQube quality gate

Gitleaks checks for leaked secrets; SonarQube analyzes bugs, vulnerabilities, and code quality. Maven generates JaCoCo coverage, then the scanner waits for the quality gate. A failed gate or unavailable/misconfigured SonarQube blocks image publication and production deployment. Only passing pushes to `main` deploy; pull requests run tests without publishing images.

**One-time setup is required:** configure the project, quality gate, `SONAR_TOKEN` secret, and repository variables using [SONARQUBE.md](SONARQUBE.md). That guide includes a deliberate-bug demonstration and local verification commands.

### GitHub and Azure configuration

The current workflow uses repository secrets `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID`, and `AZURE_SUBSCRIPTION_ID`. It deploys to `my-aks-cluster` in `my-devops-rg`. Ensure the GHCR package is accessible to AKS and the `cicd-demo` namespace exists. The historical deployment details below describe an earlier environment; confirm your current target in the workflow.

## Live Azure deployment

- GitHub repository: https://github.com/josondev/DevOps-Cia-2
- AKS cluster: `devops-cia2-aks` in `new-devops-cia2-rg` (`centralindia`)
- Public landing page: http://4.187.190.194/
- Health: http://4.187.190.194/health
- Deployed version: http://4.187.190.194/api/version
- Live deployment link: http://4.187.190.194/
- Successful pipeline run: https://github.com/josondev/DevOps-Cia-2/actions/runs/40830334794
- Security scan: Gitleaks runs as the first required GitHub Actions job.

The demo deployment uses one `Standard_D2s_v4` AKS node and two application replicas. AKS Free tier does not make the worker VM, disk, or public networking free; these resources consume Azure for Students credit while running.

The root URL serves a responsive landing page with the current deployment status, version, environment, project links, and API links. It is served by Spring Boot from the deployed container, so it is available publicly through the AKS LoadBalancer rather than only on localhost.

## Kubernetes deployment

Apply the manifests with:

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -k k8s/
```

Create the namespace once with an administrator identity. The deployment and service manifests are then applied by Kustomize in the `cicd-demo` namespace. The deployment runs two replicas and exposes the application through a `LoadBalancer` service. The CI identity can be scoped to that namespace rather than receiving cluster-wide write access.

## Ansible automation

The Ansible example in `ansible/playbook.yml` demonstrates how to create the target namespace and apply the Kubernetes manifests to a cluster.

```bash
ansible-playbook -i ansible/inventory/hosts.ini ansible/playbook.yml
```

## Security and operational considerations

- Use GitHub OIDC or secretless Azure authentication in production.
- Run Gitleaks or an equivalent secret scanner before building and deploying.
- Store registry credentials and cloud credentials in GitHub Secrets.
- Avoid exposing application secrets in YAML manifests.
- Configure image scanning and container vulnerability checks.
- Use ingress and TLS termination when exposing the app externally.

## Deployment checklist

- GitHub repository configured with the correct workflow permissions.
- Azure identity secrets configured and authorized for the target AKS cluster.
- SonarQube project and quality gate configured using [SONARQUBE.md](SONARQUBE.md).
- GHCR package visibility set to public for unauthenticated AKS image pulls.
- A custom domain and TLS ingress are not configured in this coursework demo.

## Why this design works

This solution follows the requirements of a modern end-to-end CI/CD implementation: source code is version controlled, automated tests run on every change, the application is packaged in a container, the image is pushed to a registry, and Kubernetes updates the running service without manual intervention.


sample line
# devops
