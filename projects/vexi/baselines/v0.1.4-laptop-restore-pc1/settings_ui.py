import argparse
import tkinter as tk
from tkinter import ttk, messagebox

from assistant_identity import AssistantIdentity
from credential_store import CredentialStore
from plugin_manager import PluginManager
from service_registry import ServiceRegistry
from version import __version__, __channel__


def run(initial_tab="security"):
    root=tk.Tk(); root.title(f"Vexi v{__version__} — Настройки"); root.geometry("720x500"); root.minsize(650,420)
    nb=ttk.Notebook(root); nb.pack(fill="both",expand=True,padx=12,pady=12)
    identity=AssistantIdentity(); creds=CredentialStore(); plugins=PluginManager(); services=ServiceRegistry()

    # Assistant
    f_ass=ttk.Frame(nb); nb.add(f_ass,text="Ассистент")
    ttk.Label(f_ass,text="Имя ассистента и wake-word",font=("Segoe UI",12,"bold")).pack(anchor="w",padx=16,pady=(18,8))
    name_var=tk.StringVar(value=identity.display_name())
    row=ttk.Frame(f_ass); row.pack(fill="x",padx=16,pady=6); ttk.Entry(row,textvariable=name_var,width=35).pack(side="left")
    def save_name():
        ok,val=identity.set_name(name_var.get(),source="settings_ui")
        if ok: messagebox.showinfo("Vexi",f"Новое имя: {val}. Старое wake-имя полностью заменено.")
        else: messagebox.showerror("Vexi",val)
    ttk.Button(row,text="Сохранить",command=save_name).pack(side="left",padx=8)
    def reset_name():
        val=identity.reset(); name_var.set(val); messagebox.showinfo("Vexi",f"Имя сброшено: {val}")
    ttk.Button(row,text="Сбросить",command=reset_name).pack(side="left")
    ttk.Label(f_ass,text="После сохранения Векси реагирует только на новое имя. Восстановление всегда доступно здесь, в UI.",wraplength=620).pack(anchor="w",padx=16,pady=8)

    # Plugins
    f_pl=ttk.Frame(nb); nb.add(f_pl,text="Плагины")
    ttk.Label(f_pl,text="Установленные плагины",font=("Segoe UI",12,"bold")).pack(anchor="w",padx=16,pady=(18,8))
    tree=ttk.Treeview(f_pl,columns=("version","status","browsers"),show="headings",height=12)
    for col,title,w in [("version","Версия",90),("status","Статус",150),("browsers","Браузеры",320)]: tree.heading(col,text=title); tree.column(col,width=w)
    tree.pack(fill="both",expand=True,padx=16,pady=8)
    def refresh_plugins():
        for x in tree.get_children(): tree.delete(x)
        for m in plugins.manifests():
            h=plugins.health(m); st="online" if h.get("ok") else h.get("detail","offline")
            tree.insert("", "end", values=(m.get("version","?"),st,", ".join(m.get("browser_ids",[]))))
    ttk.Button(f_pl,text="Обновить",command=refresh_plugins).pack(anchor="e",padx=16,pady=6); refresh_plugins()

    # Security
    f_sec=ttk.Frame(nb); nb.add(f_sec,text="Безопасность")
    ttk.Label(f_sec,text="Service Auth Registry",font=("Segoe UI",12,"bold")).pack(anchor="w",padx=16,pady=(18,4))
    ttk.Label(f_sec,text="Секреты вводятся только здесь и сохраняются в Windows Credential Manager. Голосом токены не принимаются.",wraplength=650).pack(anchor="w",padx=16,pady=(0,10))
    svc_ids=[s.id for s in services.list()]; svc_var=tk.StringVar(value=svc_ids[0] if svc_ids else "")
    route_var=tk.StringVar(); secret_var=tk.StringVar(); status_var=tk.StringVar(value="")
    top=ttk.Frame(f_sec); top.pack(fill="x",padx=16,pady=5)
    ttk.Label(top,text="Сервис",width=12).pack(side="left"); svc_cb=ttk.Combobox(top,textvariable=svc_var,values=svc_ids,state="readonly",width=22); svc_cb.pack(side="left")
    ttk.Label(top,text="Тип",width=8).pack(side="left",padx=(14,0)); route_cb=ttk.Combobox(top,textvariable=route_var,state="readonly",width=24); route_cb.pack(side="left")
    secrow=ttk.Frame(f_sec); secrow.pack(fill="x",padx=16,pady=5); ttk.Label(secrow,text="Секрет",width=12).pack(side="left"); entry=ttk.Entry(secrow,textvariable=secret_var,show="•",width=48); entry.pack(side="left")
    ttk.Label(f_sec,textvariable=status_var).pack(anchor="w",padx=16,pady=8)
    def current_route():
        spec=services.get(svc_var.get()); return next((r for r in (spec.auth_routes if spec else []) if r.id==route_var.get()),None)
    def refresh_routes(*_):
        spec=services.get(svc_var.get()); routes=[r.id for r in (spec.auth_routes if spec else [])]
        route_cb['values']=routes; route_var.set(routes[0] if routes else ""); secret_var.set(""); refresh_status()
    def refresh_status(*_):
        r=current_route()
        if not r: status_var.set("Для этого сервиса нет ручного секрета."); entry.config(state="disabled"); return
        if not r.manual_secret:
            status_var.set(f"{r.auth_type}: требуется отдельный OAuth flow; ручной ввод отключён."); entry.config(state="disabled"); return
        entry.config(state="normal")
        status_var.set(f"{r.auth_type}: " + ("сохранён" if creds.has(r.credential_target) else "не настроен"))
    def save_secret():
        r=current_route()
        if not r or not r.manual_secret:return
        value=secret_var.get().strip()
        if not value: messagebox.showwarning("Vexi","Введите значение."); return
        try:
            creds.write(r.credential_target,value); secret_var.set(""); refresh_status(); messagebox.showinfo("Vexi","Секрет сохранён в Windows Credential Manager.")
        except Exception as e: messagebox.showerror("Vexi",f"Не удалось сохранить: {type(e).__name__}")
    def remove_secret():
        r=current_route()
        if r and r.manual_secret:
            creds.delete(r.credential_target); secret_var.set(""); refresh_status()
    btn=ttk.Frame(f_sec); btn.pack(anchor="w",padx=16,pady=4); ttk.Button(btn,text="Сохранить",command=save_secret).pack(side="left"); ttk.Button(btn,text="Удалить",command=remove_secret).pack(side="left",padx=8)
    svc_cb.bind('<<ComboboxSelected>>',refresh_routes); route_cb.bind('<<ComboboxSelected>>',refresh_status); refresh_routes()

    tab_map={"assistant":0,"plugins":1,"security":2}
    nb.select(tab_map.get(initial_tab,2)); root.mainloop()

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--tab',default='security'); args=ap.parse_args(); run(args.tab)
