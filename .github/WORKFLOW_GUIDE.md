# GitHub CI/CD Workflow

This document describes the automated CI/CD pipeline for the Espace Image application.

## Workflow Overview

The workflow runs on every `push` and `pull_request` to `main` and `develop` branches. It consists of the following jobs that run in parallel, with deployment only occurring after all checks pass.

### Jobs

#### 1. **Lint** - Code Quality & Formatting
- **Runs on:** Ubuntu latest
- **Python Version:** 3.13
- **Steps:**
  - Checks code style using `ruff check`
  - Verifies code formatting with `ruff format --check`
- **Purpose:** Ensures consistent code style and catches potential issues early

#### 2. **Test** - Unit & Integration Tests
- **Runs on:** Ubuntu latest
- **Python Version:** 3.13
- **Services:** PostgreSQL 16 (if needed for integration tests)
- **Steps:**
  - Installs dependencies using `uv sync`
  - Runs pytest with coverage reporting
  - Uploads coverage to Codecov
- **Purpose:** Validates application functionality and maintains test coverage

#### 3. **Build Docker** - Container Build & Registry Push
- **Runs on:** Ubuntu latest
- **Steps:**
  - Sets up Docker Buildx for multi-platform builds
  - Authenticates with GitHub Container Registry (GHCR)
  - Extracts metadata (tags, labels) from git refs
  - Builds and pushes Docker image to GHCR on main/develop pushes
- **Purpose:** Creates production-ready Docker images for deployment
- **Tags Generated:**
  - Branch name (e.g., `main`, `develop`)
  - Semantic version tags (if using git tags)
  - Git SHA (commit hash)

#### 4. **Security** - Vulnerability Scanning
- **Runs on:** Ubuntu latest
- **Tool:** Trivy (container and filesystem scanning)
- **Steps:**
  - Scans filesystem for vulnerabilities
  - Uploads SARIF results to GitHub Security tab
- **Purpose:** Identifies security vulnerabilities in dependencies and code

#### 5. **Deploy** - Production Deployment
- **Runs on:** Ubuntu latest
- **Triggers:** Only on successful push to `main` branch
- **Dependencies:** Requires `lint`, `test`, and `build-docker` to pass
- **Purpose:** Deploys application to production environment
- **Note:** Currently a placeholder - customize with your actual deployment commands

## Setting Up the Workflow

### Prerequisites

1. **GitHub Secrets** - Add these to your repository settings (`Settings` → `Secrets and variables` → `Actions`):
   - `DEPLOYMENT_HOST` - Your production server/host
   - `DEPLOYMENT_KEY` - SSH key or API token for deployments
   - `CODECOV_TOKEN` - Optional: Codecov integration token

### Configuration

#### For Docker Registry Push
The workflow automatically uses GitHub's OIDC token to authenticate with GHCR. No additional secrets needed if you keep the default `GITHUB_TOKEN`.

#### For Deployment (Production)
Replace the placeholder in the `deploy` job with your actual deployment commands. Examples:

**SSH/SCP Deployment:**
```yaml
- name: Deploy to production
  run: |
    mkdir -p ~/.ssh
    echo "${{ secrets.DEPLOYMENT_KEY }}" > ~/.ssh/deploy_key
    chmod 600 ~/.ssh/deploy_key
    ssh -i ~/.ssh/deploy_key user@${{ secrets.DEPLOYMENT_HOST }} \
      'cd /app && docker pull ghcr.io/${{ github.repository }}:${{ github.ref_name }} && docker-compose up -d'
```

**Via AWS/Heroku/Other Services:**
```yaml
- name: Deploy to Heroku
  uses: akhileshns/heroku-deploy@v3.12.12
  with:
    heroku_api_key: ${{ secrets.HEROKU_API_KEY }}
    heroku_app_name: your-app-name
    heroku_email: your-email@example.com
```

## Workflow Triggers

| Event | Branches | Action |
|-------|----------|--------|
| `push` | main, develop | Run lint, test, build, security; Deploy (main only) |
| `pull_request` | main, develop | Run lint, test, build, security |

## Docker Image Tags

Images pushed to `ghcr.io/username/repo`:

- `main` - Latest main branch build
- `develop` - Latest develop branch build  
- `v1.0.0` - Semantic version (if using git tags)
- `main-abc123def` - Branch + commit SHA

Example: `ghcr.io/your-username/espace-image:main`

## Monitoring & Debugging

### View Workflow Runs
1. Go to your GitHub repository
2. Click **Actions** tab
3. View real-time logs and status

### Common Issues

**Lint Failures:**
- Fix with: `uv run ruff format .` and `uv run ruff check --fix .`

**Test Failures:**
- Check logs for specific test errors
- Ensure environment variables (like `DATABASE_URL`) are set if needed

**Docker Build Failures:**
- Verify `Dockerfile` can build locally: `docker build .`
- Check Docker syntax and layer dependencies

**GHCR Push Failures:**
- Ensure `GITHUB_TOKEN` has sufficient permissions
- Check repository visibility (might need to be public for free GHCR)

## Best Practices

1. **Keep branches protected** - Require CI/CD checks to pass before merging
2. **Review security scan results** - Address vulnerabilities promptly
3. **Monitor test coverage** - Aim for >80% coverage
4. **Use semantic versioning** - Tag releases for automatic version-tagged builds
5. **Cache Docker layers** - Workflow uses GitHub Actions cache for faster builds

## Performance Optimizations

- **uv for dependency management** - Faster than pip, deterministic builds
- **Docker layer caching** - Reduces rebuild time via GitHub Actions cache
- **Parallel job execution** - Lint, test, and build run simultaneously
- **Conditional deployment** - Only deploys on main branch after all checks

## Adding Custom Steps

Edit `.github/workflows/ci.yml` to add:
- Additional linting tools (mypy, pylint, etc.)
- Database migrations in test job
- Deployment notifications (Slack, Discord, etc.)
- Artifact uploads (build outputs, logs, etc.)

Example - Add MyPy type checking:
```yaml
- name: Type check with mypy
  run: uv run mypy app/
```

## References

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [uv Package Manager](https://docs.astral.sh/uv/)
- [Docker Build Action](https://github.com/docker/build-push-action)
- [Trivy Security Scanner](https://github.com/aquasecurity/trivy-action)
