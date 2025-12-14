#!/bin/bash
# Seed WOPR Config Service from YAML file

set -e

CONFIG_SERVICE_URL="${WOPR_CONFIG_SERVICE_URL:-http://localhost:8080}"
CONFIG_FILE="${1:-examples/config.yaml}"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Config file not found: $CONFIG_FILE"
    exit 1
fi

echo "Seeding config service at $CONFIG_SERVICE_URL"
echo "Using config file: $CONFIG_FILE"

# Read YAML file
YAML_CONTENT=$(cat "$CONFIG_FILE")

# Send to config service
curl -X POST "$CONFIG_SERVICE_URL/import/yaml" \
  -H "Content-Type: application/json" \
  -d "{\"yaml_content\": $(echo "$YAML_CONTENT" | jq -Rs .), \"updated_by\": \"seed-script\"}" \
  | jq '.'

echo ""
echo "✓ Configuration seeded successfully"
echo ""
echo "Verify with:"
echo "  curl $CONFIG_SERVICE_URL/all | jq ."
