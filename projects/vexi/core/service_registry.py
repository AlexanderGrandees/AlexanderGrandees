from dataclasses import dataclass, field


@dataclass(frozen=True)
class AuthRoute:
    id: str
    auth_type: str
    credential_target: str | None = None
    purpose: str = ""
    enabled: bool = False
    manual_secret: bool = False


@dataclass(frozen=True)
class ServiceSpec:
    id: str
    name: str
    local_route: str | None
    auth_routes: tuple[AuthRoute, ...] = field(default_factory=tuple)
    capabilities: tuple[str, ...] = field(default_factory=tuple)


SERVICES = {
    "youtube": ServiceSpec("youtube", "YouTube", "browser_pack", (
        AuthRoute("data_api", "API_KEY", "services/youtube/api_key", "public metadata/search fallback", False, True),
        AuthRoute("oauth", "OAUTH_USER", "services/youtube/oauth", "private/account APIs", False, False),
    ), ("search","page.read","media.control")),
    "github": ServiceSpec("github", "GitHub", "browser_pack", (
        AuthRoute("pat", "APP_TOKEN", "services/github/pat", "GitHub API", False, True),
        AuthRoute("oauth", "OAUTH_USER", "services/github/oauth", "user delegated API", False, False),
    ), ("read","browser.control")),
    "notion": ServiceSpec("notion", "Notion", "browser_pack", (
        AuthRoute("internal", "APP_TOKEN", "services/notion/internal_token", "Notion integration API", False, True),
        AuthRoute("oauth", "OAUTH_USER", "services/notion/oauth", "public integration", False, False),
    ), ("read","browser.control")),
    "telegram": ServiceSpec("telegram", "Telegram", "local_app", (
        AuthRoute("bot", "BOT_TOKEN", "services/telegram/bot_token", "Telegram Bot API", False, True),
    ), ("local_app","bot_api")),
    "discord": ServiceSpec("discord", "Discord", "local_app", (
        AuthRoute("bot", "BOT_TOKEN", "services/discord/bot_token", "Discord bot API", False, True),
        AuthRoute("oauth", "OAUTH_USER", "services/discord/oauth", "delegated user authorization", False, False),
    ), ("local_app","bot_api")),
    "steam": ServiceSpec("steam", "Steam", "local_app", (
        AuthRoute("web_api", "API_KEY", "services/steam/web_api_key", "Steam Web API optional metadata", False, True),
    ), ("local_app","account_picker")),
    "google": ServiceSpec("google", "Google", "browser_pack", (
        AuthRoute("oauth", "OAUTH_USER", "services/google/oauth", "Google user APIs", False, False),
    ), ("browser.control",)),
}


class ServiceRegistry:
    def list(self):
        return list(SERVICES.values())

    def get(self, service_id):
        return SERVICES.get(str(service_id).lower())

    def auth_route(self, service_id, route_id):
        spec = self.get(service_id)
        if not spec:
            return None
        return next((r for r in spec.auth_routes if r.id == route_id), None)
