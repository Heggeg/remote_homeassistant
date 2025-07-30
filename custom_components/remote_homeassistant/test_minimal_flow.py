"""Minimal options flow for testing."""
from homeassistant import config_entries
import voluptuous as vol

class MinimalOptionsFlow(config_entries.OptionsFlow):
    """Minimal options flow."""
    
    async def async_step_init(self, user_input=None):
        """Handle options flow."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
            
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional("test"): str,
            })
        )