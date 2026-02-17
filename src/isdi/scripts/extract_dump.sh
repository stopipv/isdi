#!/bin/bash

# Usage: ./extract_service.sh filename servicename

FILE="$1"
SERVICE="$2"

if [[ -z "$FILE" || -z "$SERVICE" ]]; then
  echo "Usage: $0 <filename> <service-name>"
  exit 1
fi

NEXT_SECTION_REGEX="^DUMP OF SERVICE "

sed -n "/^DUMP OF SERVICE ${SERVICE}\$/,/^DUMP OF SERVICE /{
  /^DUMP OF SERVICE ${SERVICE}\$/d
  /^DUMP OF SERVICE /q
  p
}" "$FILE"
