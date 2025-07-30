"""Config flow for Remote Home-Assistant integration."""
from __future__ import annotations
import logging
import enum
from typing import Any, Mapping

from urllib.parse import urlparse

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries, core
from homeassistant.const import (CONF_ABOVE, CONF_ACCESS_TOKEN, CONF_BELOW,
                                 CONF_ENTITY_ID, CONF_HOST, CONF_PORT,
                                 CONF_UNIT_OF_MEASUREMENT, CONF_VERIFY_SSL, CONF_TYPE)
from homeassistant.core import callback
from homeassistant.helpers.instance_id import async_get
from homeassistant.util import slugify

from . import async_yaml_to_config_entry
from .const import (CONF_ENTITY_PREFIX,  # pylint:disable=unused-import
                    CONF_ENTITY_FRIENDLY_NAME_PREFIX,
                    CONF_EXCLUDE_DOMAINS, CONF_EXCLUDE_ENTITIES, CONF_FILTER,
                    CONF_INCLUDE_DOMAINS, CONF_INCLUDE_ENTITIES,
                    CONF_LOAD_COMPONENTS, CONF_MAIN, CONF_OPTIONS, CONF_REMOTE, CONF_REMOTE_CONNECTION,
                    CONF_SECURE, CONF_SERVICE_PREFIX, CONF_SERVICES, CONF_MAX_MSG_SIZE,
                    CONF_SUBSCRIBE_EVENTS, DOMAIN, REMOTE_ID, DEFAULT_MAX_MSG_SIZE)
from .rest_api import (ApiProblem, CannotConnect, EndpointMissing, InvalidAuth,
                       UnsupportedVersion, async_get_discovery_info)
from homeassistant.helpers import selector
from .search_selector import (
    create_service_search_selector,
    create_entity_search_selector,
    create_domain_search_selector,
)

_LOGGER = logging.getLogger(__name__)

ADD_NEW_EVENT = "add_new_event"

FILTER_OPTIONS = [CONF_ENTITY_ID, CONF_UNIT_OF_MEASUREMENT, CONF_ABOVE, CONF_BELOW]


def _filter_str(index, filter_conf: Mapping[str, str|float]):
    entity_id = filter_conf[CONF_ENTITY_ID]
    unit = filter_conf[CONF_UNIT_OF_MEASUREMENT]
    above = filter_conf[CONF_ABOVE]
    below = filter_conf[CONF_BELOW]
    return f"{index+1}. {entity_id}, unit: {unit}, above: {above}, below: {below}"


async def validate_input(hass: core.HomeAssistant, conf):
    """Validate the user input allows us to connect."""
    try:
        info = await async_get_discovery_info(
            hass,
            conf[CONF_HOST],
            conf[CONF_PORT],
            conf.get(CONF_SECURE, False),
            conf[CONF_ACCESS_TOKEN],
            conf.get(CONF_VERIFY_SSL, False),
        )
    except OSError as exc:
        raise CannotConnect() from exc

    return {"title": info["location_name"], "uuid": info["uuid"]}


class InstanceType(enum.Enum):
    """Possible options for instance type."""

    remote = "Setup as remote node"
    main = "Add a remote"


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Remote Home-Assistant."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    def __init__(self):
        """Initialize a new ConfigFlow."""
        self.prefill = {CONF_PORT: 8123, CONF_SECURE: True, CONF_MAX_MSG_SIZE: DEFAULT_MAX_MSG_SIZE}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get options flow for this handler."""
        return OptionsFlowHandler()

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            if user_input[CONF_TYPE] == CONF_REMOTE:
                await self.async_set_unique_id(REMOTE_ID)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="Remote instance", data=user_input)

            elif user_input[CONF_TYPE] == CONF_MAIN:
                return await self.async_step_connection_details()
 
            errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_TYPE): vol.In([CONF_REMOTE, CONF_MAIN])
                }
            ),
            errors=errors,
        )


    async def async_step_connection_details(self, user_input=None):
        """Handle the connection details step."""
        errors = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except ApiProblem:
                errors["base"] = "api_problem"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except UnsupportedVersion:
                errors["base"] = "unsupported_version"
            except EndpointMissing:
                errors["base"] = "missing_endpoint"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(info["uuid"])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=info["title"], data=user_input)

        user_input = user_input or {}
        host = user_input.get(CONF_HOST, self.prefill.get(CONF_HOST) or vol.UNDEFINED)
        port = user_input.get(CONF_PORT, self.prefill.get(CONF_PORT) or vol.UNDEFINED)
        secure = user_input.get(CONF_SECURE, self.prefill.get(CONF_SECURE) or vol.UNDEFINED)
        max_msg_size = user_input.get(CONF_MAX_MSG_SIZE, self.prefill.get(CONF_MAX_MSG_SIZE) or vol.UNDEFINED)
        return self.async_show_form(
            step_id="connection_details",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=host): str,
                    vol.Required(CONF_PORT, default=port): int,
                    vol.Required(CONF_ACCESS_TOKEN, default=user_input.get(CONF_ACCESS_TOKEN, vol.UNDEFINED)): str,
                    vol.Required(CONF_MAX_MSG_SIZE, default=max_msg_size): int,
                    vol.Optional(CONF_SECURE, default=secure): bool,
                    vol.Optional(CONF_VERIFY_SSL, default=user_input.get(CONF_VERIFY_SSL, True)): bool,
                }
            ),
            errors=errors,
        )

    async def async_step_zeroconf(self, discovery_info):
        """Handle instance discovered via zeroconf."""
        properties = discovery_info.properties
        port = discovery_info.port
        uuid = properties["uuid"]

        await self.async_set_unique_id(uuid)
        self._abort_if_unique_id_configured()

        if await async_get(self.hass) == uuid:
            return self.async_abort(reason="already_configured")

        url = properties.get("internal_url")
        if not url:
            url = properties.get("base_url")
        url = urlparse(url)

        self.prefill = {
            CONF_HOST: url.hostname,
            CONF_PORT: port,
            CONF_SECURE: url.scheme == "https",
        }

        # pylint: disable=no-member # https://github.com/PyCQA/pylint/issues/3167
        self.context["identifier"] = self.unique_id
        self.context["title_placeholders"] = {"name": properties["location_name"]}
        return await self.async_step_connection_details()

    async def async_step_import(self, user_input):
        """Handle import from YAML."""
        try:
            info = await validate_input(self.hass, user_input)
        except Exception:
            _LOGGER.exception(f"import of {user_input[CONF_HOST]} failed")
            return self.async_abort(reason="import_failed")

        conf, options = async_yaml_to_config_entry(user_input)

        # Options cannot be set here, so store them in a special key and import them
        # before setting up an entry
        conf[CONF_OPTIONS] = options

        await self.async_set_unique_id(info["uuid"])
        self._abort_if_unique_id_configured(updates=conf)

        return self.async_create_entry(title=f"{info['title']} (YAML)", data=conf)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for the Home Assistant remote integration."""

    async def async_step_init(self, user_input : dict[str, str] | None = None):
        """Manage basic options."""
        # Initialize instance variables
        if not hasattr(self, 'options'):
            self.options = None
        
        if self.config_entry.unique_id == REMOTE_ID:
            return self.async_abort(reason="not_supported")
        
        if user_input is not None:
            self.options = user_input.copy()
            return await self.async_step_domain_entity_filters()

        domains, _ = self._domains_and_entities()
        domains = set(domains + self.config_entry.options.get(CONF_LOAD_COMPONENTS, []))

        # Check if the integration data is available
        try:
            remote = self.hass.data[DOMAIN][self.config_entry.entry_id][
                CONF_REMOTE_CONNECTION
            ]
            services_list = list(remote.proxy_services.services)
        except (KeyError, AttributeError):
            # If data is not available yet, use empty list
            services_list = []

        # Create service options with search functionality
        service_selector = create_service_search_selector(
            services=services_list,
            selected=self.config_entry.options.get(CONF_SERVICES, []),
        )
        
        # Create domain selector with entity counts
        _, entity_counts = self._organize_entities_with_counts(self._domains_and_entities()[1])
        domain_selector = create_domain_search_selector(
            domains=list(domains),
            entity_counts=entity_counts,
            selected=self.config_entry.options.get(CONF_LOAD_COMPONENTS, []),
        )
        
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_ENTITY_PREFIX,
                        description={
                            "suggested_value": self.config_entry.options.get(
                                CONF_ENTITY_PREFIX
                            )
                        },
                    ): str,
                    vol.Optional(
                        CONF_ENTITY_FRIENDLY_NAME_PREFIX,
                        description={
                            "suggested_value": self.config_entry.options.get(
                                CONF_ENTITY_FRIENDLY_NAME_PREFIX
                            )
                        },
                    ): str,
                    vol.Optional(
                        CONF_LOAD_COMPONENTS,
                        default=self._default(CONF_LOAD_COMPONENTS),
                    ): selector.selector(domain_selector),
                    vol.Required(
                        CONF_SERVICE_PREFIX, default=self.config_entry.options.get(CONF_SERVICE_PREFIX) or slugify(self.config_entry.title)
                    ): str,
                    vol.Optional(
                        CONF_SERVICES,
                        default=self._default(CONF_SERVICES),
                    ): selector.selector(service_selector),
                }
            ),
            description_placeholders={
                "components_count": str(len(domains)),
                "services_count": str(len(remote.proxy_services.services))
            }
        )

    async def async_step_domain_entity_filters(self, user_input=None):
        """Manage domain and entity filters."""
        if self.options is not None and user_input is not None:
            self.options.update(user_input)
            return await self.async_step_general_filters()

        domains, entities = self._domains_and_entities()
        organized_entities, entity_counts = self._organize_entities_with_counts(entities)
        
        # Create searchable selectors for domains and entities
        include_domain_selector = create_domain_search_selector(
            domains=domains,
            entity_counts=entity_counts,
            selected=self.config_entry.options.get(CONF_INCLUDE_DOMAINS, []),
        )
        
        exclude_domain_selector = create_domain_search_selector(
            domains=domains,
            entity_counts=entity_counts,
            selected=self.config_entry.options.get(CONF_EXCLUDE_DOMAINS, []),
        )
        
        # Create entity selectors with search
        include_entity_selector = create_entity_search_selector(
            entities=entities,
            selected=self.config_entry.options.get(CONF_INCLUDE_ENTITIES, []),
            get_friendly_name=None,  # TODO: Add friendly name support
        )
        
        exclude_entity_selector = create_entity_search_selector(
            entities=entities,
            selected=self.config_entry.options.get(CONF_EXCLUDE_ENTITIES, []),
            get_friendly_name=None,  # TODO: Add friendly name support
        )
        
        return self.async_show_form(
            step_id="domain_entity_filters",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_INCLUDE_DOMAINS,
                        default=self._default(CONF_INCLUDE_DOMAINS),
                    ): selector.selector(include_domain_selector),
                    vol.Optional(
                        CONF_INCLUDE_ENTITIES,
                        default=self._default(CONF_INCLUDE_ENTITIES),
                    ): selector.selector(include_entity_selector),
                    vol.Optional(
                        CONF_EXCLUDE_DOMAINS,
                        default=self._default(CONF_EXCLUDE_DOMAINS),
                    ): selector.selector(exclude_domain_selector),
                    vol.Optional(
                        CONF_EXCLUDE_ENTITIES,
                        default=self._default(CONF_EXCLUDE_ENTITIES),
                    ): selector.selector(exclude_entity_selector),
                }
            ),
            description_placeholders={
                "total_entities": str(len(entities)),
                "total_domains": str(len(domains))
            }
        )

    async def async_step_general_filters(self, user_input=None):
        """Manage domain and entity filters."""
        # Initialize filters if not exists
        if not hasattr(self, 'filters'):
            self.filters = None
        
        if user_input is not None:
            # Continue to next step if entity id is not specified
            if CONF_ENTITY_ID not in user_input:
                # Each filter string is prefixed with a number (index in self.filter+1).
                # Extract all of them and build the final filter list.
                selected_indices = [
                    int(filterItem.split(".")[0]) - 1
                    for filterItem in user_input.get(CONF_FILTER, [])
                ]
                if self.options is not None:
                    self.options[CONF_FILTER] = [self.filters[i] for i in selected_indices]  # type: ignore
                return await self.async_step_events()

            selected = user_input.get(CONF_FILTER, [])
            new_filter = {conf: user_input.get(conf) for conf in FILTER_OPTIONS}
            
            selected.append(_filter_str(len(self.filters), new_filter))  # type: ignore
            self.filters.append(new_filter)  # type: ignore
        else:
            self.filters = self.config_entry.options.get(CONF_FILTER, [])
            selected = [_filter_str(i, filterItem) for i, filterItem in enumerate(self.filters)] # type: ignore

        if self.filters is None:
            self.filters = []
        strings = [_filter_str(i, filterItem) for i, filterItem in enumerate(self.filters)]
        return self.async_show_form(
            step_id="general_filters",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_FILTER, default=selected): cv.multi_select(
                        strings
                    ),
                    vol.Optional(CONF_ENTITY_ID): str,
                    vol.Optional(CONF_UNIT_OF_MEASUREMENT): str,
                    vol.Optional(CONF_ABOVE): vol.Coerce(float),
                    vol.Optional(CONF_BELOW): vol.Coerce(float),
                }
            ),
        )

    async def async_step_events(self, user_input=None):
        """Manage event options."""
        # Initialize events if not exists
        if not hasattr(self, 'events'):
            self.events = None
            
        if user_input is not None:
            if ADD_NEW_EVENT not in user_input and self.options is not None:
                self.options[CONF_SUBSCRIBE_EVENTS] = user_input.get(
                    CONF_SUBSCRIBE_EVENTS, []
                )
                return self.async_create_entry(title="", data=self.options)

            selected = user_input.get(CONF_SUBSCRIBE_EVENTS, [])
            if self.events is None:
                self.events = set()
            self.events.add(user_input[ADD_NEW_EVENT])
            selected.append(user_input[ADD_NEW_EVENT])
        else:
            self.events = set(
                self.config_entry.options.get(CONF_SUBSCRIBE_EVENTS) or []
            )
            selected = self._default(CONF_SUBSCRIBE_EVENTS)

        event_options = [{"value": event, "label": event} 
                        for event in sorted(self.events if self.events else [])]
        
        return self.async_show_form(
            step_id="events",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SUBSCRIBE_EVENTS, default=selected,
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=event_options,
                            multiple=True,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                            custom_value=True,  # Allow custom event names
                        )
                    ),
                    vol.Optional(ADD_NEW_EVENT): str,
                }
            ),
            description_placeholders={
                "events_count": str(len(self.events) if self.events else 0)
            }
        )

    def _default(self, conf):
        """Return default value for an option."""
        return self.config_entry.options.get(conf) or vol.UNDEFINED

    def _create_grouped_options(self, items: list[str], group_by_domain: bool = True) -> list[dict[str, str]]:
        """Create options list with optional domain grouping."""
        if not group_by_domain:
            return [{"value": item, "label": item} for item in sorted(items)]
        
        # Group by domain
        grouped = {}
        other_items = []
        
        for item in items:
            if "." in item:
                domain, name = item.split(".", 1)
                if domain not in grouped:
                    grouped[domain] = []
                grouped[domain].append((item, name))
            else:
                other_items.append(item)
        
        # Build options list with group headers
        options = []
        for domain in sorted(grouped.keys()):
            # Add domain header as disabled option for visual grouping
            options.append({
                "value": f"__{domain}__",
                "label": f"━━━ {domain.upper()} ━━━",
                "disabled": True
            })
            # Add items in this domain
            for full_id, name in sorted(grouped[domain], key=lambda x: x[1]):
                options.append({
                    "value": full_id,
                    "label": f"  {name}"
                })
        
        # Add ungrouped items at the end
        if other_items:
            if options:  # Add separator if there are grouped items
                options.append({
                    "value": "__other__",
                    "label": "━━━ OTHER ━━━",
                    "disabled": True
                })
            for item in sorted(other_items):
                options.append({"value": item, "label": item})
        
        return options
    
    def _organize_services(self, services: list[str]) -> list[str]:
        """Organize services by domain for better display."""
        # Group by domain
        domain_services = {}
        for service in services:
            if "." in service:
                domain, svc = service.split(".", 1)
                if domain not in domain_services:
                    domain_services[domain] = []
                domain_services[domain].append(service)
            else:
                if "other" not in domain_services:
                    domain_services["other"] = []
                domain_services["other"].append(service)
        
        # Sort by domain and services within domain
        result = []
        for domain in sorted(domain_services.keys()):
            result.extend(sorted(domain_services[domain]))
        
        return result
    
    def _organize_entities_with_counts(self, entities: list[str]) -> tuple[list[str], dict[str, int]]:
        """Organize entities by domain and return counts."""
        domain_entities = {}
        for entity in entities:
            domain = entity.split(".")[0]
            if domain not in domain_entities:
                domain_entities[domain] = []
            domain_entities[domain].append(entity)
        
        # Sort by domain and entities within domain
        result = []
        counts = {}
        for domain in sorted(domain_entities.keys()):
            result.extend(sorted(domain_entities[domain]))
            counts[domain] = len(domain_entities[domain])
        
        return result, counts

    def _domains_and_entities(self):
        """Return all entities and domains exposed by remote instance."""
        # Include entities we have in the config explicitly
        include_entities = set(self.config_entry.options.get(CONF_INCLUDE_ENTITIES, []))
        exclude_entities = set(self.config_entry.options.get(CONF_EXCLUDE_ENTITIES, []))
        
        try:
            remote = self.hass.data[DOMAIN][self.config_entry.entry_id][
                CONF_REMOTE_CONNECTION
            ]
            all_entities = remote._all_entity_names | include_entities | exclude_entities
        except (KeyError, AttributeError):
            # If remote connection is not available, use only configured entities
            all_entities = include_entities | exclude_entities
        
        entities = sorted(all_entities)
        domains = sorted(set([entity_id.split(".")[0] for entity_id in entities if "." in entity_id]))
        return domains, entities
