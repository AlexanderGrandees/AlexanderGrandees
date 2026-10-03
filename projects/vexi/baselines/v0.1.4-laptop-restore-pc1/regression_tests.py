import json
import os
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
CFG = json.loads((BASE / 'config.json').read_text(encoding='utf-8'))
from version import __version__, __channel__
from site_capabilities import capability

fail=[]
def check(name, cond, detail=''):
    if cond: print('PASS',name)
    else:
        print('FAIL',name,detail); fail.append(name)

check('version-module', __version__ == '0.1.2', __version__)
check('version-config', CFG.get('version') == '0.1.2', CFG.get('version'))
check('channel', __channel__ == 'test', __channel__)
check('youtube-grid', capability('youtube','OPEN_VIDEO_BY_TITLE') == ('W0','implemented_structured_bridge'))
check('barge-in-default', CFG.get('barge_in_enabled') is True)
check('bridge-default', CFG.get('browser_bridge_enabled') is True)
check('bridge-token', bool(CFG.get('browser_bridge_token')))
check('extension-manifest', (BASE/'browser_extension'/'manifest.json').exists())
check('extension-content', (BASE/'browser_extension'/'content.js').exists())

if os.name == 'nt':
    from router import Router, contains_open, site_targets
    check('open-basic', contains_open('открой vivaldi'))
    check('open-modal', contains_open('можешь открыть youtube'))
    check('open-stt-known', contains_open('кромнее vivaldi'))
    check('site-youtube', site_targets('открой youtube') == ['youtube'])
    r=Router(CFG)
    check('class-report', r._classify_clause('YouTube не открылся') == 'REPORT')
    check('class-command', r._classify_clause('можешь открыть YouTube') == 'COMMAND')
    check('audio-minimum', r._number_word_percent('сделай громкость на минимум') == 0)
    check('youtube-structured-method', hasattr(r.youtube,'visible_videos'))
    check('youtube-open-method', hasattr(r.youtube,'open_video'))
    check('browser-bridge-method', hasattr(r.browser,'bridge_status'))
    handled, ans = r.execute('какая у тебя версия?')
    check('version-route', handled and '0.1.2' in (ans or ''), ans)
else:
    # Linux packaging smoke: Windows-specific modules cannot be imported, so
    # verify source contracts without pretending to exercise Win32.
    router_src=(BASE/'router.py').read_text(encoding='utf-8')
    vexi_src=(BASE/'vexi.py').read_text(encoding='utf-8')
    check('router-structured-youtube', 'open_video(' in router_src and 'list_visible(' in router_src)
    check('router-version-route', 'VERSION' in router_src and '__version__' in router_src)
    check('barge-in-code', 'BARGE_IN detected' in vexi_src and '_play_interruptible' in vexi_src)

if fail:
    print('\nFAILED:', ', '.join(fail)); sys.exit(1)
print('\nVEXI v0.1.2 REGRESSION SMOKE: PASS')
