# 400 Bad Request Error - Fixed!

## What Was Causing the Error

The 400 Bad Request error occurred because:
1. The config flow tries to access `/api/remote_homeassistant/discovery` on the REMOTE instance
2. This endpoint only exists if the Remote Home Assistant integration is installed on that instance
3. If it's not installed, you get a 400 error

## The Fix

Implemented a fallback discovery mechanism that:
1. First tries the custom discovery endpoint
2. If that fails (404/400), falls back to standard Home Assistant API endpoints
3. Uses `/api/` and `/api/config` to gather basic instance information
4. Creates a pseudo-UUID based on host, port, and location name

## How It Works Now

### Scenario 1: Both instances have the integration
- Works as before, using the custom discovery endpoint
- Full functionality with proper instance UUID

### Scenario 2: Only main instance has the integration
- Uses fallback discovery
- Gathers info from standard HA endpoints
- Creates consistent pseudo-UUID
- Shows warning if custom endpoint would be better

## Benefits

1. **No more 400 errors** - Works with any Home Assistant instance
2. **Better error messages** - Clear guidance on what to do
3. **Backwards compatible** - Still uses custom endpoint when available
4. **Consistent IDs** - Same remote always gets same pseudo-UUID

## Usage

Just add the integration as normal:
1. Install on your main instance
2. Add integration → "Add a remote"
3. Enter connection details
4. It will work even if remote doesn't have the integration

For best results, install on both instances and set up remote as "remote node".