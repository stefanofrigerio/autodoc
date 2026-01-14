#!/bin/bash
PROJECT_ID="it-nonprod-gen-advana-000017"
LOCATION="europe-west3"

echo "Getting access token..."
ACCESS_TOKEN=$(gcloud auth print-access-token)

if [ -z "$ACCESS_TOKEN" ]; then
    echo "Failed to get access token."
    exit 1
fi

echo "Listing models in ${LOCATION}..."
curl -v -X GET \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    "https://${LOCATION}-aiplatform.googleapis.com/v1/projects/${PROJECT_ID}/locations/${LOCATION}/publishers/google/models"
