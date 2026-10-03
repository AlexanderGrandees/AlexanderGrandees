from credential_store import CredentialStore
from service_registry import ServiceRegistry


class AuthRegistry:
    """Credential metadata only. Secret values never leave CredentialStore."""
    def __init__(self, services=None, credentials=None):
        self.services = services or ServiceRegistry()
        self.credentials = credentials or CredentialStore()

    def route_status(self, service_id, route_id):
        route = self.services.auth_route(service_id, route_id)
        if not route:
            return {"state":"NOT_CONFIGURED","detail":"unknown_auth_route"}
        if route.auth_type in {"NONE_LOCAL","EXTENSION_PERMISSION"}:
            return {"state":"CONNECTED","auth_type":route.auth_type}
        if route.auth_type == "OAUTH_USER":
            # OAuth broker is intentionally not enabled in v0.1.3.
            return {"state":"AUTH_REQUIRED","auth_type":route.auth_type,"detail":"oauth_flow_not_enabled"}
        if route.credential_target and self.credentials.has(route.credential_target):
            return {"state":"CONNECTED","auth_type":route.auth_type}
        return {"state":"NOT_CONFIGURED","auth_type":route.auth_type}

    def service_status(self, service_id):
        spec = self.services.get(service_id)
        if not spec:
            return {"service":service_id,"state":"NOT_CONFIGURED","routes":[]}
        routes=[]
        for r in spec.auth_routes:
            routes.append({"id":r.id,"enabled":bool(r.enabled),**self.route_status(service_id,r.id)})
        return {"service":service_id,"routes":routes}
