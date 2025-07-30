"""Simple implementation to call Home Assistant REST API."""

import logging
from homeassistant import exceptions
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.instance_id import async_get as async_get_instance_id

_LOGGER = logging.getLogger(__name__)

API_URL = "{proto}://{host}:{port}/api/remote_homeassistant/discovery"
FALLBACK_API_URL = "{proto}://{host}:{port}/api/"
CONFIG_API_URL = "{proto}://{host}:{port}/api/config"


class ApiProblem(exceptions.HomeAssistantError):
    """Error to indicate problem reaching API."""


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""


class BadResponse(exceptions.HomeAssistantError):
    """Error to indicate a bad response was received."""


class UnsupportedVersion(exceptions.HomeAssistantError):
    """Error to indicate an unsupported version of Home Assistant."""


class EndpointMissing(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""


async def async_get_discovery_info(hass, host, port, secure, access_token, verify_ssl):
    """Get discovery information from server."""
    proto = "https" if secure else "http"
    headers = {
        "Authorization": "Bearer " + access_token,
        "Content-Type": "application/json",
    }
    session = async_get_clientsession(hass, verify_ssl)

    # First try the custom discovery endpoint
    url = API_URL.format(proto=proto, host=host, port=port)
    try:
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                json = await resp.json()
                if isinstance(json, dict) and "uuid" in json:
                    _LOGGER.debug("Got discovery info from custom endpoint")
                    return json
            elif resp.status == 401:
                raise InvalidAuth()
            elif resp.status == 404:
                _LOGGER.debug("Custom discovery endpoint not found, trying fallback")
    except Exception as e:
        if isinstance(e, InvalidAuth):
            raise
        _LOGGER.debug("Failed to get custom discovery info: %s", e)

    # Fallback: Try standard Home Assistant API endpoints
    _LOGGER.info("Using fallback discovery method")
    
    # Get basic API info
    api_url = FALLBACK_API_URL.format(proto=proto, host=host, port=port)
    try:
        async with session.get(api_url, headers=headers) as resp:
            if resp.status == 401:
                raise InvalidAuth()
            if resp.status != 200:
                raise ApiProblem(f"API returned {resp.status}")
            api_info = await resp.json()
    except Exception as e:
        if isinstance(e, InvalidAuth):
            raise
        _LOGGER.error("Failed to connect to API: %s", e)
        raise CannotConnect() from e

    # Get config info for location name
    config_url = CONFIG_API_URL.format(proto=proto, host=host, port=port)
    try:
        async with session.get(config_url, headers=headers) as resp:
            if resp.status != 200:
                raise ApiProblem(f"Config API returned {resp.status}")
            config_info = await resp.json()
    except Exception as e:
        _LOGGER.error("Failed to get config: %s", e)
        config_info = {}

    # Check Home Assistant version
    if "message" in api_info:
        # Extract version from message like "API running."
        ha_version = None
    else:
        ha_version = None

    # Build discovery info from fallback data
    # Note: We can't get the instance UUID from the remote instance without the custom endpoint
    # So we'll use a combination of host and location name as a unique identifier
    location_name = config_info.get("location_name", f"Remote HA at {host}")
    
    # Create a pseudo-UUID based on host and port
    # This ensures the same remote instance always gets the same ID
    import hashlib
    unique_string = f"{host}:{port}:{location_name}"
    pseudo_uuid = hashlib.sha256(unique_string.encode()).hexdigest()[:32]
    
    discovery_info = {
        "uuid": pseudo_uuid,
        "location_name": location_name,
        "ha_version": config_info.get("version", "unknown"),
        "installation_type": "unknown",
        "fallback_discovery": True  # Flag to indicate this was a fallback
    }
    
    _LOGGER.info("Created fallback discovery info for %s", location_name)
    return discovery_info
