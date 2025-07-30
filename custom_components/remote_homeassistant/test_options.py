"""Test script to check if options flow can be created."""
import sys
sys.path.insert(0, '/config')

from custom_components.remote_homeassistant.config_flow import ConfigFlow, OptionsFlowHandler
from custom_components.remote_homeassistant.const import REMOTE_ID

# Mock config entry
class MockConfigEntry:
    def __init__(self):
        self.entry_id = "01K1D2BW786KHYFGK8HRC8BDE8"
        self.unique_id = "7f75dafe9b854efca48e177cdadc0031"
        self.title = "home"
        self.domain = "remote_homeassistant"
        self.options = {}

print("Testing options flow creation...")

try:
    # Test 1: Create config flow
    flow = ConfigFlow()
    print(f"ConfigFlow created: {flow}")
    
    # Test 2: Get options flow
    mock_entry = MockConfigEntry()
    options_flow = ConfigFlow.async_get_options_flow(mock_entry)
    print(f"Options flow returned: {options_flow}")
    print(f"Options flow type: {type(options_flow)}")
    
    if options_flow is None:
        print("ERROR: Options flow is None!")
    else:
        print(f"SUCCESS: Options flow created: {options_flow}")
        print(f"Has config_entry: {hasattr(options_flow, 'config_entry')}")
        print(f"Config entry ID: {options_flow.config_entry.entry_id if hasattr(options_flow, 'config_entry') else 'N/A'}")
        
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()