import logging
import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
import homeassistant.helpers.config_validation as cv
import voluptuous as vol

_LOGGER = logging.getLogger(__name__)

DOMAIN = "xkeen"
SERVICE_ADD_DOMAIN = "add_domain"

ADD_DOMAIN_SCHEMA = vol.Schema({
    vol.Required("domain"): cv.string,
    vol.Optional("rule_index", default=2): cv.positive_int,
})

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Настройка интеграции через UI."""
    url = entry.data.get("url")
    token = entry.data.get("token")

    async def handle_add_domain(call: ServiceCall):
        target_domain = call.data.get("domain")
        rule_idx = call.data.get("rule_index")

        async with aiohttp.ClientSession() as session:
            headers = {"x-api-token": token}
            try:
                # 1. Fetch
                async with session.get(f"{url}/api/fetch", headers=headers) as resp:
                    if resp.status != 200:
                        _LOGGER.error("Failed to fetch config")
                        return
                    data = await resp.json()
                
                # 2. Modify
                rules = data['routing']['routing']['rules']
                if rule_idx < len(rules):
                    if 'domain' not in rules[rule_idx]:
                        rules[rule_idx]['domain'] = []
                    if target_domain not in rules[rule_idx]['domain']:
                        rules[rule_idx]['domain'].append(target_domain)
                    else:
                        return

                # 3. Push
                payload = {"outbounds": data['outbounds'], "routing": data['routing']['routing']}
                async with session.post(f"{url}/api/push", json=payload, headers=headers) as resp:
                    if resp.status == 200:
                        _LOGGER.info(f"Domain {target_domain} added successfully")
                    else:
                        _LOGGER.error("Failed to push config")

            except Exception as e:
                _LOGGER.error(f"Connection error: {e}")

    hass.services.async_register(DOMAIN, SERVICE_ADD_DOMAIN, handle_add_domain, schema=ADD_DOMAIN_SCHEMA)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Удаление интеграции."""
    hass.services.async_remove(DOMAIN, SERVICE_ADD_DOMAIN)
    return True
