import os, queue, subprocess, sys, threading, time
from pathlib import Path
import pystray
from PIL import Image, ImageDraw
from version import __version__, __channel__, __build__

BASE=Path(__file__).resolve().parent; ICON_PATH=BASE/'vexi.ico'

def make_icon(kind="idle",size=64):
    if kind=="idle" and ICON_PATH.exists():
        try:return Image.open(ICON_PATH).convert("RGBA").resize((size,size))
        except Exception:pass
    palette={"idle":(45,160,255,255),"thinking":(165,95,255,255),"speaking":(70,220,150,255),"muted":(120,120,130,255),"error":(235,80,80,255)}; c=palette.get(kind,palette['idle'])
    img=Image.new("RGBA",(size,size),(0,0,0,0)); d=ImageDraw.Draw(img); d.ellipse((5,5,size-5,size-5),fill=(18,20,28,245),outline=c,width=4); d.ellipse((17,17,size-17,size-17),fill=c); d.ellipse((25,22,32,29),fill=(255,255,255,220)); return img

class Overlay:
    def __init__(self,identity,enabled=True,duration=2.2):
        self.identity=identity; self.enabled=enabled; self.duration=duration; self.q=queue.Queue(); threading.Thread(target=self._run,daemon=True).start()
    def show(self,status,detail=""):
        if self.enabled:self.q.put((status,detail))
    def _run(self):
        import tkinter as tk
        root=tk.Tk(); root.withdraw(); root.overrideredirect(True); root.attributes('-topmost',True); root.attributes('-alpha',.94)
        w,h=310,94; sw,sh=root.winfo_screenwidth(),root.winfo_screenheight(); root.geometry(f"{w}x{h}+{sw-w-28}+{sh-h-78}"); root.configure(bg='#11141c')
        canvas=tk.Canvas(root,width=70,height=94,bg='#11141c',highlightthickness=0); canvas.pack(side='left'); orb=canvas.create_oval(14,26,58,70,fill='#2da0ff',outline='#7cc8ff',width=3); canvas.create_oval(27,35,34,42,fill='white',outline='')
        frame=tk.Frame(root,bg='#11141c'); frame.pack(side='left',fill='both',expand=True); title=tk.Label(frame,text='',fg='white',bg='#11141c',font=('Segoe UI Semibold',12)); title.pack(anchor='w',pady=(18,0)); label=tk.Label(frame,text='Слушаю',fg='#b9c4d0',bg='#11141c',font=('Segoe UI',10)); label.pack(anchor='w'); detail_lbl=tk.Label(frame,text='',fg='#7e8b9a',bg='#11141c',font=('Segoe UI',8)); detail_lbl.pack(anchor='w')
        colors={'Слушаю':'#2da0ff','Думаю':'#a55fff','Говорю':'#46dc96','Выключена':'#777780','Включена':'#2da0ff','Ошибка':'#eb5050'}; hide_at={'t':0.0}
        def poll():
            title.config(text=f"{self.identity.display_name().upper()}  v{__version__}")
            try:
                while True:
                    status,detail=self.q.get_nowait(); c=colors.get(status,'#2da0ff'); canvas.itemconfig(orb,fill=c,outline=c); label.config(text=status); detail_lbl.config(text=detail[:48]); root.deiconify(); hide_at['t']=time.time()+self.duration
            except queue.Empty:pass
            if root.state()!='withdrawn' and hide_at['t'] and time.time()>hide_at['t']:root.withdraw()
            root.after(100,poll)
        root.after(100,poll); root.mainloop()

class Tray:
    def __init__(self,state,overlay,identity):
        self.state=state; self.overlay=overlay; self.identity=identity
        self.icon=pystray.Icon('Vexi',make_icon('idle'),f"{identity.display_name()} v{__version__} • {__channel__}")
        self.icon.menu=pystray.Menu(
            pystray.MenuItem(lambda item:f"{self.identity.display_name()} v{__version__} • {__channel__}",self.show_about,enabled=False),
            pystray.MenuItem('Ассистент включён',self.toggle,checked=lambda item:self.state.enabled),
            pystray.MenuItem('Озвучивать ответы',self.toggle_speech,checked=lambda item:self.state.speak_enabled),
            pystray.MenuItem('Показать ассистента',self.show_status),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('Настройки / Безопасность',lambda i=None,x=None:self.open_settings('security')),
            pystray.MenuItem('Плагины',lambda i=None,x=None:self.open_settings('plugins')),
            pystray.MenuItem('Имя ассистента',lambda i=None,x=None:self.open_settings('assistant')),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('О версии',self.show_about),pystray.MenuItem('Открыть лог',self.open_log),pystray.MenuItem('Открыть папку',self.open_folder),pystray.Menu.SEPARATOR,pystray.MenuItem('Выход',self.exit))
        threading.Thread(target=self.icon.run,daemon=True).start()
    def set_kind(self,kind):
        try:self.icon.icon=make_icon(kind); self.icon.title=f"{self.identity.display_name()} v{__version__} • {__channel__}"
        except Exception:pass
    def toggle(self,icon=None,item=None): self.state.enabled=not self.state.enabled; self.set_kind('idle' if self.state.enabled else 'muted'); self.overlay.show('Включена' if self.state.enabled else 'Выключена')
    def toggle_speech(self,icon=None,item=None): self.state.speak_enabled=not self.state.speak_enabled
    def show_status(self,icon=None,item=None): self.overlay.show('Слушаю' if self.state.enabled else 'Выключена',f"{self.identity.display_name()} v{__version__} • {__channel__}")
    def show_about(self,icon=None,item=None): self.overlay.show('Включена',f"{self.identity.display_name()} v{__version__} • {__channel__} • {__build__}")
    def open_log(self,icon=None,item=None): p=BASE/'logs'/'vexi.log'; p.parent.mkdir(exist_ok=True); p.touch(exist_ok=True); os.startfile(str(p))
    def open_folder(self,icon=None,item=None): os.startfile(str(BASE))
    def open_settings(self,tab='security'):
        pyw=BASE/'.venv'/'Scripts'/'pythonw.exe'; py=pyw if pyw.exists() else Path(sys.executable)
        try: subprocess.Popen([str(py),str(BASE/'settings_ui.py'),'--tab',tab],cwd=str(BASE),creationflags=0x08000000 if os.name=='nt' else 0)
        except Exception:self.overlay.show('Ошибка','Не удалось открыть настройки')
    def exit(self,icon=None,item=None): self.state.exit_requested=True; self.icon.stop()
