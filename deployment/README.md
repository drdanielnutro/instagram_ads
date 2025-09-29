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