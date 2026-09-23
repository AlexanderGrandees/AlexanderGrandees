import os, tempfile, json
from pathlib import Path
from assistant_identity import AssistantIdentity
from speech_canonicalizer import SpeechCanonicalizer
from policy_gate import PolicyGate
from service_registry import ServiceRegistry
from service_router import UniversalServiceRouter

root=Path(tempfile.mkdtemp(prefix='vexi013_test_'))
ident=AssistantIdentity('Векси',root/'identity')
assert ident.display_name()=='Векси'
ok,name=ident.set_name('Луна'); assert ok and ident.display_name()=='Луна' and ident.wake_names()==['Луна']
assert ident.reset()=='Векси'
canon=SpeechCanonicalizer(True,root/'speech')
text,changes=canon.canonicalize('включи CDR на компе')
assert 'hdr' in text.lower(), (text,changes)
text2,changes2=canon.canonicalize('открой CDR файл')
assert 'cdr' in text2.lower(), (text2,changes2)
rec=canon.observe_explicit_correction('HDR, а не CDR.')
assert rec and rec['canonical']=='hdr'
policy=PolicyGate(); assert policy.evaluate(action_class='A1',web_class='W1')=='ALLOW'; assert policy.evaluate(action_class='A4')=='DENY'; assert policy.guard_text('переведи деньги на другой счет')[0]=='DENY'
services=ServiceRegistry(); assert services.get('youtube').local_route=='browser_pack'; assert services.auth_route('youtube','data_api').auth_type=='API_KEY'
print('VEXI v0.1.3 CORE REGRESSION: PASS')

# universal router: without an installed browser pack, YouTube local route is registered but not configured
sr=UniversalServiceRouter()
d=sr.resolve('youtube','search',action_class='A1',web_class='W1'); assert d.decision in {'ALLOW','NOT_CONFIGURED'}
d2=sr.resolve('youtube','search',action_class='A4',web_class='W4',domain='financial'); assert d2.decision=='DENY'
