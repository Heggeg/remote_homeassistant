# Fix for 400 Bad Request Error in Remote Home Assistant

## Problem Analysis

The 400 Bad Request error occurs when trying to configure a new Remote Home Assistant connection. The issue is that the configuration flow tries to access the discovery endpoint (`/api/remote_homeassistant/discovery`) on the REMOTE Home Assistant instance, not the local one.

## Root Cause

1. The discovery endpoint is only registered when the Remote Home Assistant integration is installed
2. If you're trying to connect to a Home Assistant instance that doesn't have this integration installed, the endpoint won't exist
3. This causes a 400 Bad Request error when the config flow tries to validate the connection

## Current Code Flow

1. User enters connection details in config flow
2. `validate_input()` is called with the remote host details
3. `async_get_discovery_info()` tries to access `/api/remote_homeassistant/discovery` on the REMOTE host
4. If the remote host doesn't have the integration, it returns 400 Bad Request

## Solutions

### Option 1: Make Discovery Endpoint Optional (Recommended)
Modify the discovery process to gracefully handle missing endpoints:

1. Try the custom discovery endpoint first
2. If it returns 404/400, fall back to standard Home Assistant API endpoints
3. Use `/api/` or `/api/config` to get basic instance information

### Option 2: Better Error Messaging
Improve the error message to clearly indicate that the remote instance needs the integration installed.

### Option 3: Two-Step Setup Process
1. First, set up the local instance as a "remote node"
2. Then, on the main instance, add the remote connection

## Immediate Workaround

To use the integration right now:

1. Install Remote Home Assistant on BOTH instances
2. On the remote instance: Add integration and select "Setup as remote node"
3. On the main instance: Add integration and select "Add a remote"
4. Enter the connection details

## Code Changes Needed

The fix should modify `rest_api.py` to handle missing endpoints gracefully and potentially fall back to standard HA API endpoints for basic discovery information.