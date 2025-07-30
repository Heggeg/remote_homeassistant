"""Search-enabled selectors for Remote Home Assistant configuration."""
from __future__ import annotations
from typing import Any, Callable, Optional
import voluptuous as vol
from homeassistant.helpers import selector


class SearchableMultiSelectSelector(selector.SelectSelector):
    """Enhanced select selector with search functionality."""
    
    def __init__(self, config: selector.SelectSelectorConfig):
        """Initialize the searchable selector."""
        super().__init__(config)
        # Ensure we have the right settings for search functionality
        config.multiple = True
        config.mode = selector.SelectSelectorMode.DROPDOWN
        if not hasattr(config, 'custom_value'):
            config.custom_value = False


def create_searchable_selector(
    options: list[dict[str, str]], 
    selected: list[str] | None = None,
    placeholder: str = "Search and select...",
) -> dict[str, Any]:
    """Create a searchable multi-select configuration."""
    return {
        "select": {
            "options": options,
            "multiple": True,
            "mode": "dropdown",
            "custom_value": False,
            "sort": False,  # We'll handle sorting ourselves
        }
    }


def organize_options_by_domain(
    items: list[str],
    get_friendly_name: Optional[Callable[[str], str]] = None,
    show_counts: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Organize options by domain with counts and search metadata."""
    domain_items = {}
    
    for item in items:
        if "." in item:
            domain, name = item.split(".", 1)
            if domain not in domain_items:
                domain_items[domain] = []
            domain_items[domain].append(item)
        else:
            if "other" not in domain_items:
                domain_items["other"] = []
            domain_items["other"].append(item)
    
    options = []
    counts = {}
    
    # Add search hint at the top
    options.append({
        "value": "__search_hint__",
        "label": "🔍 Type to search...",
        "disabled": True,
    })
    
    # Process each domain
    for domain in sorted(domain_items.keys()):
        items_in_domain = sorted(domain_items[domain])
        counts[domain] = len(items_in_domain)
        
        # Add domain header
        header_label = f"━━━ {domain.upper()}"
        if show_counts:
            header_label += f" ({counts[domain]} items) ━━━"
        else:
            header_label += " ━━━"
            
        options.append({
            "value": f"__{domain}__",
            "label": header_label,
            "disabled": True,
        })
        
        # Add items with search-friendly labels
        for item in items_in_domain:
            _, name = item.split(".", 1) if "." in item else ("", item)
            friendly_name = get_friendly_name(item) if get_friendly_name else None
            
            label = f"  {name}"
            if friendly_name and friendly_name != name:
                label += f" ({friendly_name})"
                
            options.append({
                "value": item,
                "label": label,
                "search_terms": [
                    item.lower(),  # Full entity ID
                    name.lower(),  # Just the name part
                    domain.lower(),  # Domain
                    friendly_name.lower() if friendly_name else "",  # Friendly name
                ],
            })
    
    return options, counts


def create_service_search_selector(
    services: list[str],
    selected: list[str] | None = None,
) -> dict[str, Any]:
    """Create a searchable selector specifically for services."""
    options, _ = organize_options_by_domain(services, show_counts=True)
    return create_searchable_selector(
        options=options,
        selected=selected,
        placeholder="Search services... (e.g. 'light.turn' or 'automation')",
    )


def create_entity_search_selector(
    entities: list[str],
    selected: list[str] | None = None,
    get_friendly_name: Optional[Callable[[str], str]] = None,
) -> dict[str, Any]:
    """Create a searchable selector specifically for entities."""
    options, _ = organize_options_by_domain(
        entities, 
        get_friendly_name=get_friendly_name,
        show_counts=True,
    )
    return create_searchable_selector(
        options=options,
        selected=selected,
        placeholder="Search entities... (e.g. 'living room' or 'sensor.temp')",
    )


def create_domain_search_selector(
    domains: list[str],
    entity_counts: dict[str, int],
    selected: list[str] | None = None,
) -> dict[str, Any]:
    """Create a searchable selector specifically for domains."""
    options = [{
        "value": "__search_hint__",
        "label": "🔍 Type to search domains...",
        "disabled": True,
    }]
    
    for domain in sorted(domains):
        count = entity_counts.get(domain, 0)
        options.append({
            "value": domain,
            "label": f"{domain} ({count} entities)",
            "search_terms": [domain.lower()],
        })
    
    return create_searchable_selector(
        options=options,
        selected=selected,
        placeholder="Search domains... (e.g. 'light' or 'sensor')",
    )