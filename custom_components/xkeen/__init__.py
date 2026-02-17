import logging
import voluptuous as vol
import aiohttp
import json
import homeassistant.helpers.config_validation as cv
from homeassistant.core import HomeAssistant, ServiceCall

_LOGGER = logging.getLogger(__name__)

DOMAIN = "xkeen"
CONF_URL = "url"
CONF_TOKEN = "token"

# Описание параметров для сервиса добавления домена
SERVICE_ADD_DOMAIN = "add_domain"
ATTR_DOMAIN = "domain"
ATTR_RULE_INDEX = "rule_index" # По умолчанию 2 (обычно там VPS список)

ADD_DOMAIN_SCHEMA = vol.Schema({
    vol.Required(ATTR_DOMAIN): cv.string,
    vol.Optional(ATTR_RULE_INDEX, default=2): cv.positive_int,
})

async def async_setup(hass: HomeAssistant, config: dict):
    """Настройка интеграции xKeen через configuration.yaml."""
    conf = config.get(DOMAIN)
    if conf is None:
        return True

    url = conf.get(CONF_URL)
    token = conf.get(CONF_TOKEN)

    async def handle_add_domain(call: ServiceCall):
        """Логика добавления домена через API xkeen-ui."""
        target_domain = call.data.get(ATTR_DOMAIN)
        rule_idx = call.data.get(ATTR_RULE_INDEX)

        # 1. Fetch current config
        async with aiohttp.ClientSession() as session:
            headers = {"x-api-token": token}
            try:
                # Получаем текущие файлы
                async with session.get(f"{url}/api/fetch", headers=headers) as resp:
                    if resp.status != 200:
                        _LOGGER.error("Failed to fetch config from xkeen-ui")
                        return
                    data = await resp.json()
                    
                outbounds = data['outbounds']
                routing = data['routing']

                # 2. Modify routing
                rules = routing['routing']['rules']
                if rule_idx < len(rules):
                    if 'domain' not in rules[rule_idx]:
                        rules[rule_idx]['domain'] = []
                    
                    if target_domain not in rules[rule_idx]['domain']:
                        rules[rule_idx]['domain'].append(target_domain)
                        _LOGGER.info(f"Adding {target_domain} to rule {rule_idx}")
                    else:
                        _LOGGER.info(f"Domain {target_domain} already exists")
                        return

                # 3. Push back
                payload = {
                    "outbounds": outbounds,
                    "routing": routing['routing']
                }
                async with session.post(f"{url}/api/push", json=payload, headers=headers) as resp:
                    if resp.status == 200:
                        hass.bus.async_fire("xkeen_config_updated", {"domain": target_domain})
                    else:
                        _LOGGER.error("Failed to push updated config to xkeen-ui")

            except Exception as e:
                _LOGGER.error(f"Error connecting to xkeen-ui: {e}")

    hass.services.async_register(DOMAIN, SERVICE_ADD_DOMAIN, handle_add_domain, schema=ADD_DOMAIN_SCHEMA)

    return True
