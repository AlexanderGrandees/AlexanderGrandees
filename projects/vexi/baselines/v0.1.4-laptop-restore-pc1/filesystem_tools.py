import logging
import os
import re
import subprocess
from pathlib import Path
from difflib import SequenceMatcher

BLOCK_OPEN_EXTS = {'.exe', '.msi', '.bat', '.cmd', '.ps1', '.vbs', '.js', '.scr', '.com'}


def norm(value):
    value = (value or '').lower().replace('ё', 'е').strip()
    value = re.sub(r'[^\w\s.\-\\/:]', ' ', value, flags=re.UNICODE)
    return re.sub(r'\s+', ' ', value).strip()


class FileSystemTools:
    def __init__(self):
        home = Path.home()
        self.roots = {
            'desktop': home / 'Desktop',
            'downloads': home / 'Downloads',
            'documents': home / 'Documents',
            'pictures': home / 'Pictures',
        }
        onedrive = os.environ.get('OneDrive')
        if onedrive:
            od = Path(onedrive)
            for key, name in [('desktop', 'Desktop'), ('documents', 'Documents'), ('pictures', 'Pictures')]:
                p = od / name
                if p.exists():
                    self.roots[key] = p
        self.aliases = {
            'desktop': ('рабочий стол', 'рабочем столе', 'рабочего стола', 'десктоп', 'desktop'),
            'downloads': ('загрузки', 'загрузках', 'скачивания', 'downloads'),
            'documents': ('документы', 'документах', 'documents'),
            'pictures': ('картинки', 'изображения', 'фото', 'pictures'),
        }
        self.last_found = None

    def root_from_text(self, text):
        t = norm(text)
        for key, aliases in self.aliases.items():
            if any(a in t for a in aliases):
                return self.roots.get(key)
        return None

    def open_path(self, path, select=False):
        p = Path(path)
        if not p.exists():
            return False
        if select and p.is_file():
            subprocess.Popen(['explorer.exe', '/select,', str(p)])
        else:
            os.startfile(str(p))
        return True

    def _score(self, query, name):
        q = norm(query)
        n = norm(name)
        if q == n:
            return 1.0
        if q in n:
            return 0.92
        return SequenceMatcher(None, q, n).ratio()

    def find(self, query, max_files=12000):
        q = norm(query)
        if not q:
            return []
        matches = []
        seen = set()
        count = 0
        for root in self.roots.values():
            if not root or not Path(root).exists():
                continue
            for dirpath, dirs, files in os.walk(root):
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                for name in files:
                    count += 1
                    if count > max_files:
                        break
                    path = Path(dirpath) / name
                    if path in seen:
                        continue
                    seen.add(path)
                    score = self._score(q, name)
                    if score >= 0.62 or q in norm(str(path)):
                        matches.append((score, path))
                if count > max_files:
                    break
            if count > max_files:
                break
        matches.sort(key=lambda x: (x[0], x[1].stat().st_mtime if x[1].exists() else 0), reverse=True)
        return [p for _, p in matches[:5]]

    def execute(self, text):
        t = norm(text)

        # Open a known user folder.
        if any(x in t for x in ('открой', 'покажи')):
            root = self.root_from_text(t)
            if root and Path(root).exists() and not ('файл' in t or 'найди' in t):
                self.open_path(root)
                logging.info('ACTION filesystem.open_folder path=%s', root)
                return True, f'Открываю {Path(root).name}.'

        # Find file by name/fragment.
        m = re.search(r'(?:найди|поищи)\s+(?:мне\s+)?(?:файл\s+)?(.+)$', t)
        file_intent = ('файл' in t) or (self.root_from_text(t) is not None)
        if m and file_intent and not any(x in t for x in ('youtube', 'ютуб', 'гугл', 'google', 'браузер')):
            query = m.group(1).strip()
            results = self.find(query)
            if not results:
                logging.info('ACTION filesystem.find query=%s result=none', query)
                return True, f'В основных папках файл «{query}» не нашла.'
            best = results[0]
            self.last_found = best
            self.open_path(best, select=True)
            logging.info('ACTION filesystem.find query=%s best=%s count=%s', query, best, len(results))
            extra = '' if len(results) == 1 else f' Ещё похожих: {len(results)-1}.'
            return True, f'Нашла {best.name}. Открыла папку и выделила файл.{extra}'

        # Open a file safely by semantic/name search.
        m = re.search(r'открой\s+(?:мне\s+)?(?:файл\s+)?(.+)$', t)
        explicit_file = ('файл' in t) or bool(re.search(r'\.[a-zа-я0-9]{1,6}(?:\s|$)', t))
        if m and explicit_file and 'папк' not in t:
            query = m.group(1).strip()
            if self.root_from_text(query):
                return False, None
            results = self.find(query)
            if results:
                best = results[0]
                if best.suffix.lower() in BLOCK_OPEN_EXTS:
                    return True, 'Нашла исполняемый файл, но через файловый модуль его не запускаю. Используй команду запуска приложения.'
                os.startfile(str(best))
                self.last_found = best
                logging.info('ACTION filesystem.open_file path=%s', best)
                return True, f'Открываю {best.name}.'

        # Create folder in a known user root.
        m = re.search(r'создай\s+папку\s+(.+?)(?:\s+(?:в|на)\s+(.+))?$', t)
        if m:
            name = m.group(1).strip(' .')
            destination_text = m.group(2) or ''
            root = self.root_from_text(destination_text) or self.roots.get('desktop')
            if not name or any(x in name for x in ('\\', '/', ':', '*', '?', '"', '<', '>', '|')):
                return True, 'Название папки выглядит небезопасно. Ничего не создала.'
            target = Path(root) / name
            target.mkdir(parents=False, exist_ok=True)
            ok = target.exists() and target.is_dir()
            logging.info('ACTION filesystem.create_folder path=%s verified=%s', target, ok)
            return True, f'Папка {name} создана.' if ok else 'Не смогла подтвердить создание папки.'

        return False, None
