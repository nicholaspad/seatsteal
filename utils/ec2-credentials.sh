#!/bin/bash

# EC2 Credentials Helper
# Provides functions to store/retrieve EC2 credentials from Supabase database
# This allows credentials to persist across terminal-server redeployments on Render.
#
# Required environment variables:
#   SUPABASE_URL - e.g., https://xxx.supabase.co
#   SUPABASE_SERVICE_ROLE_KEY - service role key for admin access
#
# Usage: Source this file in other scripts
#   source "$SCRIPT_DIR/ec2-credentials.sh"
#   sync_credentials || true

# Get script directory for file path resolution
CRED_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CRED_REPO_ROOT="$(dirname "$CRED_SCRIPT_DIR")"
LOCAL_PEM="$CRED_REPO_ROOT/seatsteal.pem"
LOCAL_HOST_JSON="$CRED_SCRIPT_DIR/ec2-host.json"

# Check if Supabase credentials are available
_has_supabase_creds() {
    [[ -n "$SUPABASE_URL" ]] && [[ -n "$SUPABASE_SERVICE_ROLE_KEY" ]]
}

# Store credentials in Supabase
# Usage: store_credentials <pem_file> <json_file>
store_credentials() {
    local pem_file="$1"
    local json_file="$2"

    if ! _has_supabase_creds; then
        echo "Supabase credentials not configured, skipping remote storage"
        return 0
    fi

    if [[ ! -f "$pem_file" ]]; then
        echo "Error: PEM file not found: $pem_file"
        return 1
    fi

    if [[ ! -f "$json_file" ]]; then
        echo "Error: JSON file not found: $json_file"
        return 1
    fi

    echo "Storing credentials in Supabase..."

    # First, deactivate all existing active credentials
    curl -s -X PATCH \
        "${SUPABASE_URL}/rest/v1/ec2_credentials?is_active=eq.true" \
        -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
        -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}" \
        -H "Content-Type: application/json" \
        -H "Prefer: return=minimal" \
        -d '{"is_active": false}' > /dev/null

    # Read PEM contents and escape for JSON
    local pem_contents
    pem_contents=$(cat "$pem_file")

    # Read host info JSON
    local host_info
    host_info=$(cat "$json_file")

    # Create JSON payload using jq to properly escape strings
    local payload
    payload=$(jq -n \
        --arg pem "$pem_contents" \
        --argjson host "$host_info" \
        '{pem_contents: $pem, host_info: $host, is_active: true}')

    # Insert new credentials
    local response
    response=$(curl -s -w "\n%{http_code}" -X POST \
        "${SUPABASE_URL}/rest/v1/ec2_credentials" \
        -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
        -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}" \
        -H "Content-Type: application/json" \
        -H "Prefer: return=minimal" \
        -d "$payload")

    local http_code
    http_code=$(echo "$response" | tail -n1)

    if [[ "$http_code" == "201" ]]; then
        echo "Credentials stored in Supabase successfully"
        return 0
    else
        echo "Warning: Failed to store credentials in Supabase (HTTP $http_code)"
        return 1
    fi
}

# Retrieve credentials from Supabase and write to local files
# Usage: retrieve_credentials
retrieve_credentials() {
    if ! _has_supabase_creds; then
        return 1
    fi

    echo "Retrieving credentials from Supabase..."

    # Get the latest active credentials
    local response
    response=$(curl -s \
        "${SUPABASE_URL}/rest/v1/ec2_credentials?is_active=eq.true&order=created_at.desc&limit=1" \
        -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
        -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}" \
        -H "Accept: application/json")

    # Check if we got valid data
    if [[ -z "$response" ]] || [[ "$response" == "[]" ]]; then
        echo "No active credentials found in Supabase"
        return 1
    fi

    # Extract PEM contents and write to file
    local pem_contents
    pem_contents=$(echo "$response" | jq -r '.[0].pem_contents // empty')

    if [[ -z "$pem_contents" ]]; then
        echo "Error: Could not extract PEM contents from Supabase response"
        return 1
    fi

    echo "$pem_contents" > "$LOCAL_PEM"
    chmod 400 "$LOCAL_PEM"
    echo "SSH key written to: $LOCAL_PEM"

    # Extract host info and write to file
    local host_info
    host_info=$(echo "$response" | jq -r '.[0].host_info // empty')

    if [[ -z "$host_info" ]]; then
        echo "Error: Could not extract host info from Supabase response"
        return 1
    fi

    echo "$host_info" | jq '.' > "$LOCAL_HOST_JSON"
    echo "Host info written to: $LOCAL_HOST_JSON"

    return 0
}

# Deactivate all credentials in Supabase (called on termination)
# Usage: delete_credentials
delete_credentials() {
    if ! _has_supabase_creds; then
        echo "Supabase credentials not configured, skipping remote deletion"
        return 0
    fi

    echo "Deactivating credentials in Supabase..."

    local response
    response=$(curl -s -w "\n%{http_code}" -X PATCH \
        "${SUPABASE_URL}/rest/v1/ec2_credentials?is_active=eq.true" \
        -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
        -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}" \
        -H "Content-Type: application/json" \
        -H "Prefer: return=minimal" \
        -d '{"is_active": false}')

    local http_code
    http_code=$(echo "$response" | tail -n1)

    if [[ "$http_code" == "200" ]] || [[ "$http_code" == "204" ]]; then
        echo "Credentials deactivated in Supabase"
        return 0
    else
        echo "Warning: Failed to deactivate credentials in Supabase (HTTP $http_code)"
        return 1
    fi
}

# Check if active credentials exist in Supabase
# Usage: has_remote_credentials
has_remote_credentials() {
    if ! _has_supabase_creds; then
        return 1
    fi

    local response
    response=$(curl -s \
        "${SUPABASE_URL}/rest/v1/ec2_credentials?is_active=eq.true&select=id&limit=1" \
        -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
        -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}" \
        -H "Accept: application/json")

    # Check if we got a non-empty array
    if [[ -n "$response" ]] && [[ "$response" != "[]" ]]; then
        return 0
    else
        return 1
    fi
}

# Sync credentials from Supabase if local files don't exist
# Usage: sync_credentials
# Returns: 0 if credentials available (locally or from remote), 1 if no credentials
sync_credentials() {
    # If both local files exist, no need to sync
    if [[ -f "$LOCAL_PEM" ]] && [[ -f "$LOCAL_HOST_JSON" ]]; then
        return 0
    fi

    # Check if we can retrieve from Supabase
    if ! _has_supabase_creds; then
        # No Supabase creds and no local files
        return 1
    fi

    # Check if remote credentials exist
    if ! has_remote_credentials; then
        return 1
    fi

    # Retrieve from Supabase
    retrieve_credentials
}
