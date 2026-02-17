import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
import aiohttp
import yarl

DOMAIN = "xkeen"

class XKeenConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for xKeen."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Валидация URL
            url = user_input.get("url")
            try:
                yarl.URL(url)
                # Простая проверка связи
                async with aiohttp.ClientSession() as session:
                    headers = {"x-api-token": user_input.get("token")}
                    async with session.get(f"{url}/api/settings", headers=headers, timeout=5) as resp:
                        if resp.status == 401:
                            errors["base"] = "invalid_auth"
                        elif resp.status != 200:
                            errors["base"] = "cannot_connect"
                        else:
                            return self.async_create_entry(title="xKeen Configurator", data=user_input)
            except Exception:
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("url", default="http://192.168.0.89:3000"): str,
                vol.Required("token"): str,
            }),
            errors=errors,
        )
