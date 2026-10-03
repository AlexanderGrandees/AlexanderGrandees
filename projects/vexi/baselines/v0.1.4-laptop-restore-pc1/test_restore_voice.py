import ast,types,unittest,logging,time
from pathlib import Path
from unittest.mock import Mock
from speech_input import meaningful_speech,small_talk_key,SMALL_TALK
p=Path(__file__).with_name('vexi.py'); tree=ast.parse(p.read_text(encoding='utf-8'))
loop=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='assistant_loop')
class VoiceRestoreTests(unittest.TestCase):
 def test_conversation_and_legacy_actions(self):
  state=types.SimpleNamespace(exit_requested=False,enabled=True)
  heard=iter(['Векси','хмм мм','как дела','открой вивальди','открой ютуб','пауза'])
  actions=Mock();actions.execute.return_value=(True,'Готово');brain=Mock();tts=Mock();tts.speak.return_value=None
  def record(*args):
   try:return next(heard)
   except StopIteration:state.exit_requested=True;return None
  def extract(t,i):return (True,t[5:].strip()) if t.lower().startswith('векси') else (False,'')
  ns=dict(STT=lambda:types.SimpleNamespace(transcribe=lambda x:x),TTS=lambda:tts,Actions=lambda *a,**k:actions,Brain=lambda **k:brain,CFG={'onboarding_enabled':False},logging=logging,__version__='test',__channel__='test',__build__='test',os=__import__('os'),BASE=p.parent,time=time,record_utterance=record,meaningful_speech=meaningful_speech,extract_activation=extract,CANONICALIZER=types.SimpleNamespace(canonicalize=lambda x:(x,[])),is_close_phrase=lambda x:False,small_talk_key=small_talk_key,SMALL_TALK=SMALL_TALK,norm=lambda x:x,sd=types.SimpleNamespace(PortAudioError=OSError))
  exec(compile(ast.Module(body=[loop],type_ignores=[]),'voice-loop','exec'),ns)
  ns['assistant_loop'](state,Mock(),Mock(),Mock())
  self.assertEqual([x.args[0] for x in actions.execute.call_args_list],['открой вивальди','открой ютуб','пауза'])
  brain.ask.assert_not_called()
  self.assertIn(SMALL_TALK['как дела'],[x.args[0] for x in tts.speak.call_args_list])
  self.assertEqual(tts.speak.call_count,5)
if __name__=='__main__':unittest.main()
