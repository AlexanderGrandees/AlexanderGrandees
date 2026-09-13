import re


class PolicyGate:
    """Strict Vexi profile inheriting Intelligence governance.

    W0/W1 and A0/A1 are automatic when resolved. Reversible account mutation
    requires a user confirmation contract. Material communication and all
    financial/legal/security-sensitive side effects are denied in this release.
    """
    HIGH_RISK_PATTERNS = (
        r"\b(?:переведи|отправь|выведи|сними)\s+(?:деньги|средства|крипт|биткоин|евро|доллар)",
        r"\b(?:купи|продай|открой|закрой)\s+(?:ордер|позици|сделк)",
        r"\b(?:оплати|заплати|pay|withdraw|withdrawal)\b",
        r"\b(?:подай|отправь|подпиши)\s+(?:иск|заявлен|апелляц|возражен|договор|контракт)\b",
        r"\b(?:смени|измени|сбрось)\s+(?:пароль|2fa|двухфактор|права доступа|permissions)\b",
        r"\b(?:удали аккаунт|закрой аккаунт|передай права|дай админ)\b",
    )

    def evaluate(self, *, action_class="A0", web_class="W0", domain="general"):
        if domain in {"financial","legal_external","security","medical","identity"}:
            return "DENY"
        if action_class == "A4" or web_class == "W4":
            return "DENY"
        if action_class == "A3" or web_class == "W3":
            return "DENY"
        if action_class in {"A2"} or web_class == "W2":
            return "REQUIRE_APPROVAL"
        return "ALLOW"

    def guard_text(self, text):
        t = (text or "").lower().replace("ё","е")
        for p in self.HIGH_RISK_PATTERNS:
            if re.search(p, t):
                return "DENY", "Эта команда относится к действиям повышенной ответственности. В текущем профиле Векси такие действия заблокированы."
        return None
