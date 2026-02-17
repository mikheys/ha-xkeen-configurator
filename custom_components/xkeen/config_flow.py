import voluptuous as vol
from homeassistant import config_entries
import aiohttp
import yarl

DOMAIN = "xkeen"

class XKeenConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            url = user_input.get("url").rstrip("/")
            token = user_input.get("token")
            try:
                async with aiohttp.ClientSession() as session:
                    headers = {"x-api-token": token}
                    # Тестируем именно fetch, так как он требует токен
                    async with session.get(f"{url}/api/fetch", headers=headers, timeout=10) as resp:
                        if resp.status == 401:
                            errors["base"] = "invalid_auth"
                        elif resp.status != 200:
                            errors["base"] = "cannot_connect"
                        else:
                            return self.async_create_entry(title="xKeen", data=user_input)
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
