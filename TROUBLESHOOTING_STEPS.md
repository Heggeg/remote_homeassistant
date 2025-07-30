# Troubleshooting Steps for Invalid Handler Error

## The Issue
- Backend is working correctly (debug log confirms)
- Frontend returns "Invalid handler" 
- This is a Home Assistant frontend issue, not a code issue

## Try These Steps (in order):

### 1. Clear Browser Cache
- Press Ctrl+Shift+R (or Cmd+Shift+R on Mac) for hard refresh
- Or open browser settings and clear cache for your HA URL

### 2. Check Integration Health
1. Go to Settings → Devices & Services
2. Find "Remote Home-Assistant" 
3. Look for any error indicators
4. Click the 3 dots → Reload

### 3. Try Different Browser
- Test in an incognito/private window
- Or try a completely different browser

### 4. Check Developer Tools → Application → Storage
1. Open F12 Developer Tools
2. Go to Application tab
3. Clear Site Data
4. Refresh the page

### 5. Remove and Re-add Integration
If nothing else works:
1. Settings → Devices & Services
2. Find Remote Home-Assistant
3. Click 3 dots → Delete
4. Restart Home Assistant
5. Add the integration again

### 6. Check for Errors in Configuration
Look for any errors in:
- Settings → System → Logs
- Configuration → Server Controls → Check Configuration

## Why This Happens
The "Invalid handler" error typically occurs when:
- The frontend JavaScript is out of sync with the backend
- The config entry is in an inconsistent state
- Browser cache contains old data
- Multiple instances/tabs are open

## Note About URL Errors
The malformed URLs in the console (`http://...https://...`) have been fixed in the code, but this is a separate issue from the Invalid handler error.