# Deployment

This directory contains the Terraform configurations for provisioning the necessary Google Cloud infrastructure for your agent.

The recommended way to deploy the infrastructure and set up the CI/CD pipeline is by using the `agent-starter-pack setup-cicd` command from the root of your project.

However, for a more hands-on approach, you can always apply the Terraform configurations manually for a do-it-yourself setup.

For detailed information on the deployment process, infrastructure, and CI/CD pipelines, please refer to the official documentation:

**[Agent Starter Pack Deployment Guide](https://googlecloudplatform.github.io/agent-starter-pack/guide/deployment.html)**

## Google Cloud Storage permissions for tracing

The FastAPI server exports tracing spans to Cloud Logging and optionally stores large payloads in a GCS bucket. Make sure the runtime identity (usually `instagram-ads-sa@instagram-ads-472021.iam.gserviceaccount.com`) can read the bucket metadata and upload objects:

```bash
gcloud storage buckets add-iam-policy-binding gs://instagram-ads-472021-facilitador-logs-data \
  --member=serviceAccount:instagram-ads-sa@instagram-ads-472021.iam.gserviceaccount.com \
  --role=roles/storage.objectCreator

gcloud storage buckets add-iam-policy-binding gs://instagram-ads-472021-facilitador-logs-data \
  --member=serviceAccount:instagram-ads-sa@instagram-ads-472021.iam.gserviceaccount.com \
  --role=roles/storage.legacyBucketReader
```

When running locally without bucket access, disable the exporter by setting `TRACING_DISABLE_GCS=true`. The exporter will log a warning instead of raising exceptions if permissions are missing.

## Environment Variables Configuration

### Overview

The application uses environment variables loaded from `app/.env` to configure runtime behavior. These variables are automatically loaded at application startup using `python-dotenv` in `app/__init__.py` before any other imports occur.

### How It Works

1. **Loading Mechanism**: [app/__init__.py](../app/__init__.py) loads `app/.env` using `load_dotenv()` **before** importing any other modules
2. **Automatic Discovery**: All variables in `app/.env` are automatically printed to stdout during startup
3. **Configuration Override**: Values from `.env` override default values defined in [app/config.py](../app/config.py)

### Startup Logs

When running `make dev`, you'll see all environment variables loaded:

```
================================================================================
✅ ENVIRONMENT VARIABLES LOADED FROM: /home/.../app/.env
================================================================================
  GOOGLE_CLOUD_PROJECT: instagram-ads-472021
  ARTIFACTS_BUCKET: gs://instagram-ads-472021-facilitador-logs-data
  ENABLE_STORYBRAND_FALLBACK: true
  VERTEX_CONCURRENCY_LIMIT: 1
  ... (all other variables from .env)
================================================================================
```

### Adding New Environment Variables

To add a new environment variable:

1. Add it to `app/.env`:
   ```bash
   MY_NEW_FLAG=true
   ```

2. **No code changes needed** - it will automatically appear in startup logs

3. (Optional) If you need to use it in code, add override logic in `app/config.py`:
   ```python
   if os.getenv("MY_NEW_FLAG"):
       config.my_new_flag = os.getenv("MY_NEW_FLAG").lower() == "true"
   ```

### Key Feature Flags

- `ENABLE_STORYBRAND_FALLBACK`: Enable fallback pipeline when StoryBrand analysis fails (default: `false`)
- `ENABLE_NEW_INPUT_FIELDS`: Enable experimental input fields (default: `false`)
- `STORYBRAND_GATE_DEBUG`: Force fallback path for testing (default: `false`)
- `ENABLE_IMAGE_GENERATION`: Enable Gemini image generation (default: `true`)
- `PREFLIGHT_SHADOW_MODE`: Extract new fields without including in initial_state (default: `true`)

**Important**: The fallback pipeline only activates when **both** `ENABLE_STORYBRAND_FALLBACK=true` **AND** `ENABLE_NEW_INPUT_FIELDS=true`, plus one of:
- `STORYBRAND_GATE_DEBUG=true` (forces fallback)
- StoryBrand score below threshold (default 0.6)
- `force_storybrand_fallback=true` in state

See [app/agents/storybrand_gate.py](../app/agents/storybrand_gate.py) for gate logic.

### Troubleshooting

**Problem**: Environment variables not loading

**Solution**:
1. Verify `app/.env` exists
2. Check startup logs for `✅ ENVIRONMENT VARIABLES LOADED FROM` message
3. Restart with `make dev` (kills ports and reloads everything)
4. Test directly: `bash -c 'set -a; source app/.env; set +a; uv run python -c "import os; print(os.getenv(\"YOUR_VAR\"))"'`

**Technical Note**: The Makefile's `dev-backend-all` target also loads `.env` via bash, but this is redundant since `app/__init__.py` already handles it. The primary loading mechanism is through `python-dotenv` in the Python code.