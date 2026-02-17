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
    url = entry.data.get("url").rstrip("/")
    token = entry.data.get("token")

    async def handle_add_domain(call: ServiceCall):
        target_domain = call.data.get("domain")
        tag = call.data.get("outbound_tag")
        
        _LOGGER.info(f"xKeen: Adding {target_domain} to tag {tag}")

        async with aiohttp.ClientSession() as session:
            headers = {"x-api-token": token}
            try:
                # 1. Fetch
                async with session.get(f"{url}/api/fetch", headers=headers, timeout=10) as resp:
                    if resp.status != 200:
                        _LOGGER.error(f"xKeen Fetch Failed: {resp.status}")
                        return
                    data = await resp.json()
                
                # 2. Smart Find
                # data['routing'] содержит { "routing": { "rules": [...] } }
                routing_obj = data['routing']
                rules = routing_obj['routing']['rules']
                target_rule = None
                
                for rule in rules:
                    if rule.get('outboundTag') == tag:
                        if 'domain' in rule:
                            target_rule = rule
                            break
                
                if not target_rule:
                    _LOGGER.error(f"xKeen Error: No rule with tag '{tag}' found")
                    return

                if target_domain in target_rule['domain']:
                    _LOGGER.warning(f"xKeen: {target_domain} already exists")
                    return

                target_rule['domain'].append(target_domain)

                # 3. Push
                # ВАЖНО: Мы должны отправить объект В ТОЙ ЖЕ СТРУКТУРЕ, что получили
                payload = {
                    "outbounds": data['outbounds'], # Это уже { "outbounds": [...] }
                    "routing": routing_obj          # Это должно быть { "routing": { "rules": [...] } }
                }
                
                async with session.post(f"{url}/api/push", json=payload, headers=headers, timeout=15) as resp:
                    if resp.status == 200:
                        _LOGGER.info(f"xKeen: Successfully added {target_domain}")
                    else:
                        _LOGGER.error(f"xKeen Push Failed: {resp.status}")

            except Exception as e:
                _LOGGER.error(f"xKeen Connection Error: {e}")

    hass.services.async_register(DOMAIN, SERVICE_ADD_DOMAIN, handle_add_domain, schema=ADD_DOMAIN_SCHEMA)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.services.async_remove(DOMAIN, SERVICE_ADD_DOMAIN)
    return True
