from plugin_manager import PluginManager

BUILTIN = {
    "system.audio": {"provider":"core", "risk":"A1"},
    "system.display": {"provider":"core", "risk":"A1"},
    "app.window": {"provider":"core", "risk":"A1/A2"},
    "filesystem.read": {"provider":"core", "risk":"A0"},
}


class CapabilityRegistry:
    def __init__(self, plugins=None):
        self.plugins=plugins or PluginManager()

    def providers(self, capability):
        out=[]
        if capability in BUILTIN:
            out.append({"plugin_id":"core", **BUILTIN[capability]})
        for m in self.plugins.manifests():
            if capability in (m.get("capabilities") or []):
                out.append(m)
        return out
