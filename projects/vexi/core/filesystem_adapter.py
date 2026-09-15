import logging
import os
import re
import shutil
from difflib import SequenceMatcher
from pathlib import Path

from send2trash import send2trash

BLOCK_OPEN_EXTS = {'.exe', '.msi', '.bat', '.cmd', '.ps1', '.vbs', '.js', '.scr', '.com'}


def norm(value):
    value = (value or '').lower().replace('ё', 'е').strip()
    value = re.sub(r'[^\w\s.\-\\/:]', ' ', value, flags=re.UNICODE)
    return re.sub(r'\s+', ' ', value).strip()


class FileSystemAdapter:
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
            'desktop': ('рабочий стол', 'рабочем столе', 'десктоп', 'desktop'),
            'downloads': ('загрузки', 'загрузках', 'скачивания', 'downloads'),
            'documents': ('документы', 'документах', 'documents'),
            'pictures': ('картинки', 'изображения', 'фото', 'pictures'),
        }
        self.last_found = None
        self.last_created = None
        self.last_move = None

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
            os.spawnl(os.P_NOWAIT, os.path.expandvars(r'%WINDIR%\explorer.exe'), 'explorer.exe', '/select,', str(p))
        else:
            os.startfile(str(p))
        return True

    def _score(self, query, name):
        q, n = norm(query), norm(name)
        if q == n:
            return 1.0
        if q in n:
            return 0.94
        return SequenceMatcher(None, q, n).ratio()

    def find(self, query, max_files=15000):
        q = norm(query)
        if not q:
            return []
        matches, seen, count = [], set(), 0
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
        matches.sort(key=lambda x: (-x[0], -x[1].stat().st_mtime if x[1].exists() else 0))
        return [p for _, p in matches[:25]]

    def open_known_folder(self, text):
        root = self.root_from_text(text)
        if not root:
            return None
        ok = self.open_path(root)
        if ok:
            logging.info('ACTION filesystem.open_folder path=%s', root)
            return f'Открываю {Path(root).name}.'
        return 'Не смогла открыть папку.'

    def find_file(self, query, select=True):
        results = self.find(query)
        if not results:
            return 'NOT_FOUND', None, f'В основных папках файл «{query}» не нашла.'
        best = results[0]
        self.last_found = best
        if select:
            self.open_path(best, select=True)
        logging.info('ACTION filesystem.find query=%s best=%s count=%s', query, best, len(results))
        extra = '' if len(results) == 1 else f' Ещё похожих: {len(results)-1}.'
        return 'CONFIRMED_SUCCESS', best, f'Нашла {best.name}.{extra}'

    def open_file(self, query):
        status, best, msg = self.find_file(query, select=False)
        if not best:
            return status, msg
        if best.suffix.lower() in BLOCK_OPEN_EXTS:
            return 'BLOCKED', 'Нашла исполняемый файл, но файловый модуль его не запускает. Используй запуск приложения.'
        try:
            os.startfile(str(best))
            return 'SENT_NOT_CONFIRMED', f'Команду открыть {best.name} отправила.'
        except Exception:
            return 'FAILED', f'Не смогла открыть {best.name}.'

    def create_folder(self, name, destination_text=''):
        name = name.strip(' .')
        if not name or any(x in name for x in ('\\', '/', ':', '*', '?', '"', '<', '>', '|')):
            return 'BLOCKED', 'Название папки выглядит небезопасно. Ничего не создала.'
        root = self.root_from_text(destination_text) or self.roots.get('desktop')
        target = Path(root) / name
        try:
            target.mkdir(parents=False, exist_ok=True)
            self.last_created = target
            ok = target.exists() and target.is_dir()
            logging.info('ACTION filesystem.create_folder path=%s verified=%s', target, ok)
            return ('CONFIRMED_SUCCESS' if ok else 'SENT_NOT_CONFIRMED'), (f'Папка {name} создана.' if ok else 'Создание отправила, но проверить папку не смогла.')
        except Exception as exc:
            logging.exception('create_folder failed: %s', exc)
            return 'FAILED', 'Не смогла создать папку.'

    def move_last_found(self, destination_text, copy=False):
        src = self.last_found
        if not src or not Path(src).exists():
            return 'NOT_FOUND', 'Сначала найди файл, с которым нужно работать.'
        root = self.root_from_text(destination_text)
        if not root:
            return 'AMBIGUOUS', 'Не поняла папку назначения.'
        dst = Path(root) / Path(src).name
        try:
            if copy:
                shutil.copy2(src, dst)
            else:
                shutil.move(str(src), str(dst))
            ok = dst.exists()
            self.last_move = {'src': str(src), 'dst': str(dst), 'copy': copy}
            self.last_found = dst
            action = 'copy' if copy else 'move'
            logging.info('ACTION filesystem.%s src=%s dst=%s verified=%s', action, src, dst, ok)
            return ('CONFIRMED_SUCCESS' if ok else 'SENT_NOT_CONFIRMED'), (f'Файл {"скопирован" if copy else "перемещён"} в {Path(root).name}.' if ok else 'Команду отправила, но результат не подтверждён.')
        except Exception as exc:
            logging.exception('move/copy failed: %s', exc)
            return 'FAILED', 'Не смогла выполнить операцию с файлом.'

    def trash_last_found(self):
        src = self.last_found
        if not src or not Path(src).exists():
            return 'NOT_FOUND', 'Сначала найди файл или папку, которую нужно отправить в корзину.'
        try:
            send2trash(str(src))
            ok = not Path(src).exists()
            logging.info('ACTION filesystem.trash path=%s verified=%s', src, ok)
            self.last_found = None
            return ('CONFIRMED_SUCCESS' if ok else 'SENT_NOT_CONFIRMED'), ('Отправила в корзину.' if ok else 'Команду на корзину отправила, но проверка не завершилась.')
        except Exception as exc:
            logging.exception('trash failed: %s', exc)
            return 'FAILED', 'Не смогла отправить объект в корзину.'
