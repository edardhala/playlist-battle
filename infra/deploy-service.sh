#!/usr/bin/env bash
set -euo pipefail

service=$1
image=$2
password=$3
shift 3

app="$PREFIX-$service"
db_url="mssql://${service}_user:${password}@${SQL_HOST}:1433/${PREFIX}-${service}-db"

if az containerapp show -g "$RG" -n "$app" -o none 2>/dev/null; then
  az containerapp secret set -g "$RG" -n "$app" --secrets "database-url=$db_url" -o none
  az containerapp update -g "$RG" -n "$app" \
    --image "$image" \
    --min-replicas 0 --max-replicas 1 \
    --set-env-vars "DATABASE_URL=secretref:database-url" "$@" \
    -o none
else
  az containerapp create -g "$RG" -n "$app" \
    --environment "$ENV_NAME" \
    --image "$image" \
    --ingress external --target-port 8000 \
    --cpu 0.25 --memory 0.5Gi \
    --min-replicas 0 --max-replicas 1 \
    --secrets "database-url=$db_url" \
    --env-vars "DATABASE_URL=secretref:database-url" "$@" \
    -o none
fi

az containerapp show -g "$RG" -n "$app" --query properties.configuration.ingress.fqdn -o tsv
