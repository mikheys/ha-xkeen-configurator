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
    vol.Required("outbound_tag"): cv.string,
})

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    url = entry.data.get("url")
    token = entry.data.get("token")

    async def handle_add_domain(call: ServiceCall):
        target_domain = call.data.get("domain")
        tag = call.data.get("outbound_tag")

        async with aiohttp.ClientSession() as session:
            headers = {"x-api-token": token}
            try:
                # 1. Fetch
                async with session.get(f"{url}/api/fetch", headers=headers) as resp:
                    if resp.status != 200:
                        _LOGGER.error(f"Failed to fetch: {resp.status}")
                        return
                    data = await resp.json()
                
                # 2. Smart Rule Selection
                rules = data['routing']['routing']['rules']
                target_rule = None
                
                for rule in rules:
                    # Ищем правило с нужным тегом, в котором либо уже есть домены, 
                    # либо нет IP (чтобы не перепутать с правилом для IP)
                    if rule.get('outboundTag') == tag:
                        if 'domain' in rule or 'ip' not in rule:
                            target_rule = rule
                            break
                
                if target_rule:
                    if 'domain' not in target_rule:
                        target_rule['domain'] = []
                    if target_domain not in target_rule['domain']:
                        target_rule['domain'].append(target_domain)
                        _LOGGER.info(f"Successfully added {target_domain} to {tag}")
                    else:
                        _LOGGER.info(f"Domain {target_domain} already exists in {tag}")
                        return
                else:
                    _LOGGER.error(f"Compatible rule for domains with tag '{tag}' not found")
                    return

                # 3. Push
                payload = {
                    "outbounds": data['outbounds'], 
                    "routing": data['routing']['routing']
                }
                async with session.post(f"{url}/api/push", json=payload, headers=headers) as resp:
                    if resp.status == 200:
                        _LOGGER.info("Configuration updated and pushed")
                    else:
                        _LOGGER.error(f"Failed to push: {resp.status}")

            except Exception as e:
                _LOGGER.error(f"Connection failed: {e}")

    hass.services.async_register(DOMAIN, SERVICE_ADD_DOMAIN, handle_add_domain, schema=ADD_DOMAIN_SCHEMA)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.services.async_remove(DOMAIN, SERVICE_ADD_DOMAIN)
    return True
