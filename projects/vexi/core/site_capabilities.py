"""Declarative web-service capability registry for Vexi v0.1.2.

The registry separates *what a service conceptually supports* from what the
current runtime has actually implemented.  Router/adapter code must not treat a
planned capability as executable until its implementation status allows it.
"""

ACCESS_TIERS = {
    "W0": "Public/read-only navigation and search; no account mutation.",
    "W1": "Reversible session/UI control such as tab/player/navigation state.",
    "W2": "Account-scoped reversible mutation; explicit user command required.",
    "W3": "External publication/communication or meaningful account mutation; explicit intent and verification required.",
    "W4": "Financial, security, destructive, purchase or identity-sensitive action; mandatory confirmation or blocked by default.",
}

SITE_REGISTRY = {
    "youtube": {
        "base_url": "https://www.youtube.com",
        "aliases": ["youtube", "ютуб", "ютьюб"],
        "objects": [
            "home", "search", "search_result", "video", "channel", "playlist",
            "player", "short", "subscription", "history", "comment", "account",
        ],
        "capabilities": {
            "OPEN_HOME": ("W0", "implemented"),
            "SEARCH": ("W0", "implemented"),
            "SEARCH_CHANNEL": ("W0", "implemented"),
            "OPEN_VIDEO_BY_TITLE": ("W0", "implemented_structured_bridge"),
            "OPEN_CHANNEL_BY_NAME": ("W0", "planned_structured_dom"),
            "READ_ACTIVE_VIDEO": ("W0", "implemented_structured_bridge"),
            "PLAY_PAUSE": ("W1", "implemented_structured_bridge_with_fallback"),
            "SEEK": ("W1", "implemented_structured_bridge_with_fallback"),
            "PLAYER_FULLSCREEN": ("W1", "implemented_structured_bridge_with_fallback"),
            "CAPTIONS": ("W1", "implemented_best_effort"),
            "PLAYBACK_RATE": ("W1", "implemented_structured_bridge"),
            "PLAYER_VOLUME": ("W1", "implemented_structured_bridge"),
            "NEXT_VIDEO": ("W1", "implemented_best_effort"),
            "PREVIOUS_VIDEO": ("W1", "implemented_best_effort"),
            "MINIPLAYER": ("W1", "implemented_best_effort"),
            "LIKE": ("W2", "planned_structured_dom"),
            "SAVE_TO_PLAYLIST": ("W2", "planned_structured_dom"),
            "SUBSCRIBE": ("W2", "planned_structured_dom"),
            "COMMENT": ("W3", "planned_structured_dom"),
            "DELETE_COMMENT": ("W3", "planned_structured_dom"),
            "PURCHASE_MEMBERSHIP": ("W4", "blocked_default"),
            "ACCOUNT_SECURITY": ("W4", "blocked_default"),
        },
    },
    "google": {
        "base_url": "https://www.google.com",
        "aliases": ["google", "гугл"],
        "objects": ["home", "search", "search_result"],
        "capabilities": {"OPEN_HOME": ("W0", "implemented"), "SEARCH": ("W0", "implemented")},
    },
    "gmail": {
        "base_url": "https://mail.google.com",
        "aliases": ["gmail", "джимейл"],
        "objects": ["inbox", "thread", "message", "draft", "label", "attachment"],
        "capabilities": {
            "OPEN": ("W0", "implemented"), "SEARCH": ("W0", "planned_connector_or_dom"),
            "READ": ("W0", "planned_connector_or_dom"), "DRAFT": ("W2", "planned_connector_or_dom"),
            "SEND": ("W3", "planned_connector_or_dom"), "ARCHIVE": ("W2", "planned_connector_or_dom"),
            "TRASH": ("W3", "planned_connector_or_dom"),
        },
    },
    "calendar": {
        "base_url": "https://calendar.google.com",
        "aliases": ["google calendar", "гугл календарь"],
        "objects": ["calendar", "event", "invite"],
        "capabilities": {
            "OPEN": ("W0", "implemented"), "READ": ("W0", "planned_connector_or_dom"),
            "CREATE_EVENT": ("W2", "planned_connector_or_dom"), "UPDATE_EVENT": ("W2", "planned_connector_or_dom"),
            "DELETE_EVENT": ("W3", "planned_connector_or_dom"), "RESPOND_INVITE": ("W3", "planned_connector_or_dom"),
        },
    },
    "github": {
        "base_url": "https://github.com",
        "aliases": ["github", "гитхаб"],
        "objects": ["repository", "issue", "pull_request", "commit", "branch", "release", "workflow"],
        "capabilities": {
            "OPEN": ("W0", "implemented"), "READ": ("W0", "planned_connector_or_dom"),
            "CREATE_ISSUE": ("W2", "planned_connector_or_dom"), "COMMENT": ("W3", "planned_connector_or_dom"),
            "CREATE_PR": ("W3", "planned_connector_or_dom"), "MERGE_PR": ("W4", "confirmation_required"),
            "DELETE_REPO": ("W4", "blocked_default"), "MANAGE_SECRETS": ("W4", "blocked_default"),
        },
    },
    "notion": {
        "base_url": "https://www.notion.so",
        "aliases": ["notion", "ноушн"],
        "objects": ["page", "database", "data_source", "view", "comment", "file"],
        "capabilities": {
            "OPEN": ("W0", "implemented"), "SEARCH": ("W0", "planned_connector_or_dom"),
            "READ": ("W0", "planned_connector_or_dom"), "CREATE_PAGE": ("W2", "planned_connector_or_dom"),
            "UPDATE_PAGE": ("W2", "planned_connector_or_dom"), "DELETE_CONTENT": ("W3", "confirmation_required"),
            "SCHEMA_CHANGE": ("W4", "confirmation_required"),
        },
    },
    "chatgpt": {
        "base_url": "https://chatgpt.com",
        "aliases": ["chatgpt", "чатгпт", "чат gpt"],
        "objects": ["home", "chat", "project"],
        "capabilities": {"OPEN": ("W0", "implemented"), "UI_NAVIGATION": ("W1", "planned_structured_dom")},
    },
    "tradingview": {
        "base_url": "https://www.tradingview.com",
        "aliases": ["tradingview", "трейдингвью", "трейдинг вью"],
        "objects": ["chart", "symbol", "watchlist", "layout", "alert", "broker_panel"],
        "capabilities": {
            "OPEN": ("W0", "implemented"), "READ_CHART_STATE": ("W0", "planned_structured_dom"),
            "CHANGE_SYMBOL": ("W1", "planned_structured_dom"), "CHANGE_TIMEFRAME": ("W1", "planned_structured_dom"),
            "CREATE_ALERT": ("W3", "confirmation_required"), "PLACE_ORDER": ("W4", "blocked_default"),
        },
    },
    "binance": {
        "base_url": "https://www.binance.com",
        "aliases": ["binance", "бинанс"],
        "objects": ["market", "asset", "spot", "futures", "order", "wallet", "account"],
        "capabilities": {
            "OPEN": ("W0", "implemented"), "PUBLIC_MARKET_READ": ("W0", "planned_api_or_dom"),
            "ACCOUNT_READ": ("W2", "planned_dedicated_adapter"), "PLACE_ORDER": ("W4", "blocked_default"),
            "WITHDRAW": ("W4", "blocked_default"), "SECURITY_SETTINGS": ("W4", "blocked_default"),
        },
    },
    "steam_support": {
        "base_url": "https://help.steampowered.com/",
        "aliases": ["steam support", "поддержка steam", "поддержка стим"],
        "objects": ["support_home", "product", "ticket", "account_recovery"],
        "capabilities": {
            "OPEN": ("W0", "implemented"), "BROWSE": ("W0", "planned_structured_dom"),
            "SUBMIT_TICKET": ("W3", "confirmation_required"), "ACCOUNT_RECOVERY": ("W4", "confirmation_required"),
        },
    },
}


def site_url(key):
    return (SITE_REGISTRY.get(key) or {}).get("base_url")


def capability(site, action):
    return ((SITE_REGISTRY.get(site) or {}).get("capabilities") or {}).get(action)
