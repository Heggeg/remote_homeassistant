# Config Flow 400 Error - Fixed!

## What Was Happening

The error "Der Konfigurationsfluss konnte nicht geladen werden: 400: Bad Request" was occurring because:

1. The search selector functions were returning incorrect format for Home Assistant
2. The selector configuration dict was malformed
3. Home Assistant couldn't parse the config flow schema

## The Fix

Updated `search_selector.py` to return properly formatted selector configurations:

### Before:
```python
return {
    "type": "select",
    "options": options,
    "multiple": True,
    # ... other fields
}
```

### After:
```python
return {
    "select": {
        "options": options,
        "multiple": True,
        "mode": "dropdown",
        "custom_value": False,
        "sort": False,
    }
}
```

## Why This Works

- Home Assistant's `selector.selector()` expects a dict with the selector type as key
- The selector config should be nested under the type key ("select")
- Removed unnecessary fields that were causing parsing issues

## Testing

After restarting Home Assistant:
1. Go to Settings → Devices & Services
2. Click "+ Add Integration"
3. Search for "Remote Home Assistant"
4. The config flow should now load without errors

## Note

Both fixes are now in place:
1. Config flow selector format (this fix)
2. Fallback discovery mechanism (previous fix)

Together these ensure smooth setup of Remote Home Assistant connections.