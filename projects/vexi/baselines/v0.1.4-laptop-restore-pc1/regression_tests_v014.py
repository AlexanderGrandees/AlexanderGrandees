import os
import tempfile
import json
import ast
from pathlib import Path

from assistant_identity import AssistantIdentity
from speech_canonicalizer import SpeechCanonicalizer
from policy_gate import PolicyGate
from service_registry import ServiceRegistry
from service_router import UniversalServiceRouter
from plugin_manager import PluginManager

root = Path(tempfile.mkdtemp(prefix='vexi014_test_'))
ident = AssistantIdentity('Векси', root/'identity')
assert ident.display_name() == 'Векси'
ok, name = ident.set_name('Луна')
assert ok and ident.display_name() == 'Луна' and ident.wake_names() == ['Луна']
assert ident.reset() == 'Векси'

canon = SpeechCanonicalizer(True, root/'speech')
text, changes = canon.canonicalize('включи CDR на компе')
assert 'hdr' in text.lower(), (text, changes)
text2, changes2 = canon.canonicalize('открой CDR файл')
assert 'cdr' in text2.lower(), (text2, changes2)

policy = PolicyGate()
assert policy.evaluate(action_class='A1', web_class='W1') == 'ALLOW'
assert policy.evaluate(action_class='A4') == 'DENY'

services = ServiceRegistry()
assert services.get('youtube').local_route == 'browser_pack'
sr = UniversalServiceRouter()
assert sr.resolve('youtube', 'search', action_class='A4', web_class='W4', domain='financial').decision == 'DENY'

# Legacy BOM browser-pack manifests must be accepted by Core v0.1.4.
plugdir = root/'plugins'
plugdir.mkdir()
data = {
    'plugin_id': 'vexi.browser.chrome',
    'type': 'browser_pack',
    'version': '0.1.2',
    'protocol': 1,
    'browser_ids': ['chrome'],
    'endpoint': 'http://127.0.0.1:8766'
}
(plugdir/'vexi.browser.chrome.json').write_bytes(b'\xef\xbb\xbf' + json.dumps(data).encode('utf-8'))
pm = PluginManager(plugdir)
assert pm.browser_pack('chrome')['plugin_id'] == 'vexi.browser.chrome'

# Router source must contain field-test regression routes.
src = (Path(__file__).parent/'router.py').read_text(encoding='utf-8')
ast.parse(src)
for needle in ('OBSERVE_ACTIVE_SURFACE', 'сверни', 'youtube_player', 'выйди из полноэкран', 'что ты видишь'):
    assert needle in src, needle

print('VEXI v0.1.4 CORE REGRESSION: PASS')
