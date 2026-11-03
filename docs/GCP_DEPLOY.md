# Deploying TalentTrack to Google Cloud Platform

## The architecture

```
 Browser ──HTTPS──▶ Cloud Run (container: gunicorn + Django + built React)
                        │  unix socket /cloudsql/...
                        ▼
                    Cloud SQL (PostgreSQL)

 Secret Manager ──▶ DJANGO_SECRET_KEY, DB_PASSWORD (injected as env vars)
 Artifact Registry ──▶ stores the Docker images
 Cloud Build ──▶ test → build → push → migrate → deploy  (cloudbuild.yaml)
 Cloud Logging ──▶ collects everything the app prints to stdout
```

| GCP service | What it does here | Why this one |
|---|---|---|
| **Cloud Run** | Runs the Docker container, scales 0→N automatically | Serverless: no VMs to manage, pay per request, free tier |
| **Cloud SQL** | Managed PostgreSQL | Backups, patches, HA handled by Google |
| **Secret Manager** | Stores passwords/keys | Secrets never live in code or the image |
| **Artifact Registry** | Private Docker image registry | Replaces the older Container Registry |
| **Cloud Build** | CI/CD pipeline | Native to GCP, triggered by GitHub pushes |
| **Cloud Storage** (optional) | Would store uploaded résumé files | Cloud Run's disk is temporary |

## One-time setup (copy-paste)

You need a Google account with billing enabled (new accounts get free credits) and the
[gcloud CLI](https://cloud.google.com/sdk/docs/install).

```bash
# 1. Pick names
export PROJECT_ID=talenttrack-demo-123     # must be globally unique
export REGION=asia-southeast1              # Singapore, closest to PH

gcloud projects create $PROJECT_ID
gcloud config set project $PROJECT_ID
gcloud services enable run.googleapis.com sqladmin.googleapis.com \
  artifactregistry.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com

# 2. Image registry
gcloud artifacts repositories create talenttrack --repository-format=docker --location=$REGION

# 3. Database (smallest tier; this is the part that costs money, delete it after your demo)
gcloud sql instances create talenttrack-db --database-version=POSTGRES_16 \
  --tier=db-f1-micro --region=$REGION
gcloud sql databases create talenttrack --instance=talenttrack-db
gcloud sql users create talenttrack --instance=talenttrack-db --password="CHOOSE_A_PASSWORD"

# 4. Secrets
printf "CHOOSE_A_PASSWORD" | gcloud secrets create db-password --data-file=-
python -c "import secrets;print(secrets.token_urlsafe(50),end='')" | gcloud secrets create django-secret-key --data-file=-

# 5. Let Cloud Run and Cloud Build read secrets and reach Cloud SQL
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
for SA in $PROJECT_NUMBER-compute@developer.gserviceaccount.com $PROJECT_NUMBER@cloudbuild.gserviceaccount.com; do
  gcloud projects add-iam-policy-binding $PROJECT_ID --member=serviceAccount:$SA --role=roles/secretmanager.secretAccessor
  gcloud projects add-iam-policy-binding $PROJECT_ID --member=serviceAccount:$SA --role=roles/cloudsql.client
  gcloud projects add-iam-policy-binding $PROJECT_ID --member=serviceAccount:$SA --role=roles/run.admin
  gcloud projects add-iam-policy-binding $PROJECT_ID --member=serviceAccount:$SA --role=roles/iam.serviceAccountUser
done
```

## Deploy

From the project root:

```bash
gcloud builds submit --config cloudbuild.yaml --substitutions=SHORT_SHA=v1
```

Cloud Build prints the service URL at the end (`https://talenttrack-xxxx.a.run.app`).
Seed demo data once with a one-off job:

```bash
gcloud run jobs execute talenttrack-migrate --region $REGION \
  --args manage.py,seed_demo --wait
```

## Cheaper option for a portfolio demo (no Cloud SQL)

Skip steps 3–4 and deploy with SQLite. Data resets whenever Cloud Run restarts the
container, which is fine for a demo:

```bash
gcloud run deploy talenttrack --source . --region $REGION --allow-unauthenticated \
  --set-env-vars DJANGO_ALLOWED_HOSTS=.run.app,DJANGO_SECRET_KEY=$(python -c "import secrets;print(secrets.token_urlsafe(40))") \
  --command bash --args "-c,python manage.py migrate && python manage.py seed_demo && exec gunicorn config.wsgi --bind :8080 --threads 8"
```

## Useful commands to know for the interview

```bash
gcloud run services list                           # what's deployed
gcloud run services logs read talenttrack --limit 50   # recent logs
gcloud run revisions list --service talenttrack    # every deploy is a revision
gcloud run services update-traffic talenttrack --to-revisions REVISION=100   # instant rollback
gcloud sql connect talenttrack-db --user=talenttrack   # psql into the DB
```

## Clean up (stop charges)

```bash
gcloud sql instances delete talenttrack-db
gcloud run services delete talenttrack --region $REGION
```
