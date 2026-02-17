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
    url = entry.data.get("url").rstrip("/") # Убираем слеш в конце если есть
    token = entry.data.get("token")

    async def handle_add_domain(call: ServiceCall):
        target_domain = call.data.get("domain")
        tag = call.data.get("outbound_tag")
        
        _LOGGER.debug(f"Attempting to add domain {target_domain} to tag {tag} at {url}")

        async with aiohttp.ClientSession() as session:
            headers = {"x-api-token": token}
            try:
                # 1. Fetch
                async with session.get(f"{url}/api/fetch", headers=headers, timeout=10) as resp:
                    if resp.status != 200:
                        _LOGGER.error(f"Failed to fetch config. Status: {resp.status}. URL: {url}/api/fetch")
                        return
                    data = await resp.json()
                
                # 2. Smart Rule Selection
                rules = data['routing']['routing']['rules']
                target_rule = None
                
                for rule in rules:
                    if rule.get('outboundTag') == tag:
                        # Ищем правило, где домены - это список (array)
                        if 'domain' in rule and isinstance(rule['domain'], list):
                            target_rule = rule
                            break
                        # Если списка нет, но это подходящий тег и в нем нет IP
                        if 'domain' not in rule and 'ip' not in rule:
                            target_rule = rule
                            break
                
                if target_rule:
                    if 'domain' not in target_rule:
                        target_rule['domain'] = []
                    if target_domain not in target_rule['domain']:
                        target_rule['domain'].append(target_domain)
                        _LOGGER.info(f"Added {target_domain} to rule with tag {tag}")
                    else:
                        _LOGGER.warning(f"Domain {target_domain} already exists in {tag}")
                        return
                else:
                    _LOGGER.error(f"No valid rule with outboundTag '{tag}' found for domains")
                    return

                # 3. Push
                # Важно: убираем наши служебные поля типа _expanded перед отправкой
                payload = {
                    "outbounds": data['outbounds'], 
                    "routing": data['routing']['routing']
                }
                
                async with session.post(f"{url}/api/push", json=payload, headers=headers, timeout=10) as resp:
                    if resp.status == 200:
                        _LOGGER.info("Config successfully pushed to router")
                    else:
                        _LOGGER.error(f"Failed to push config. Status: {resp.status}")

            except Exception as e:
                _LOGGER.error(f"XKeen integration error: {e}")

    hass.services.async_register(DOMAIN, SERVICE_ADD_DOMAIN, handle_add_domain, schema=ADD_DOMAIN_SCHEMA)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.services.async_remove(DOMAIN, SERVICE_ADD_DOMAIN)
    return True
