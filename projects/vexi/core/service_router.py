from dataclasses import dataclass, asdict

from auth_registry import AuthRegistry
from plugin_manager import PluginManager
from policy_gate import PolicyGate
from service_registry import ServiceRegistry


@dataclass
class RouteDecision:
    service: str
    capability: str
    decision: str
    provider: str | None = None
    auth_state: str | None = None
    action_class: str = "A0"
    web_class: str = "W0"
    reason: str = ""

    def as_dict(self):
        return asdict(self)


class UniversalServiceRouter:
    """One service-routing algorithm for local/browser/API integrations.

    v0.1.3 deliberately prefers local deterministic routes. Official APIs may be
    registered, but are not selected until the route is explicitly enabled and
    its authentication/approval contract is satisfied.
    """
    def __init__(self, services=None, auth=None, plugins=None, policy=None):
        self.services = services or ServiceRegistry()
        self.auth = auth or AuthRegistry(self.services)
        self.plugins = plugins or PluginManager()
        self.policy = policy or PolicyGate()

    def _local_available(self, spec):
        if spec.local_route == "browser_pack":
            # Site-specific command will choose the user's active/preferred pack.
            return any(m.get("type") == "browser_pack" for m in self.plugins.manifests())
        if spec.local_route == "local_app":
            return True
        return False

    def resolve(self, service_id, capability, *, action_class="A0", web_class="W0", domain="general"):
        spec = self.services.get(service_id)
        if not spec:
            return RouteDecision(service_id,capability,"UNSUPPORTED",reason="unknown_service")
        gate = self.policy.evaluate(action_class=action_class,web_class=web_class,domain=domain)
        if gate == "DENY":
            return RouteDecision(service_id,capability,"DENY",action_class=action_class,web_class=web_class,reason="policy_denied")
        if gate == "REQUIRE_APPROVAL":
            return RouteDecision(service_id,capability,"REQUIRE_APPROVAL",action_class=action_class,web_class=web_class,reason="approval_contract_required")
        if capability not in spec.capabilities:
            return RouteDecision(service_id,capability,"UNSUPPORTED",action_class=action_class,web_class=web_class,reason="capability_not_registered")
        if spec.local_route and self._local_available(spec):
            return RouteDecision(service_id,capability,"ALLOW",provider=spec.local_route,auth_state="CONNECTED",action_class=action_class,web_class=web_class,reason="local_first")
        for route in spec.auth_routes:
            if not route.enabled:
                continue
            st=self.auth.route_status(service_id,route.id).get("state")
            if st == "CONNECTED":
                return RouteDecision(service_id,capability,"ALLOW",provider=f"api:{route.id}",auth_state=st,action_class=action_class,web_class=web_class,reason="enabled_api_route")
            return RouteDecision(service_id,capability,"AUTH_REQUIRED",provider=f"api:{route.id}",auth_state=st,action_class=action_class,web_class=web_class,reason="api_auth_required")
        return RouteDecision(service_id,capability,"NOT_CONFIGURED",provider=spec.local_route,action_class=action_class,web_class=web_class,reason="provider_not_available")
