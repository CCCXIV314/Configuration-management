import base64
import csv
import os

class VFSNode:
    """Узел виртуальной файловой системы (файл или папка)."""
    def __init__(self, name, is_dir, parent=None):
        self.name = name
        self.is_dir = is_dir
        self.children = {} if is_dir else None
        self.content = "" if not is_dir else None
        self.parent = parent  # ссылка на родителя (None для root)

    def path(self):
        """Возвращает полный путь от корня до этого узла."""
        parts = []
        node = self
        while node and node.parent is not None:
            parts.append(node.name)
            node = node.parent
        if not parts:
            return "/"
        return "/" + "/".join(reversed(parts))


class VirtualFileSystem:
    """Виртуальная файловая система, полностью в памяти."""
    def __init__(self):
        self.root = VFSNode("/", True, parent=None)
        self.cwd = self.root

    def _norm_parts(self, path):
        """Нормализует путь строкой в список частей (не включает пустые)."""
        if path is None or path == "":
            return []
        return [p for p in path.split("/") if p]

    def add_node(self, path, is_dir, content=None):
        """
        Добавляет узел по абсолютному или относительному пути.
        Если путь == "/" — ничего не делает (root уже есть).
        Создаёт промежуточные директории по необходимости.
        """
        if not path:
            return

        # Если путь абсолютный — начинаем с корня, иначе — от cwd
        if path.startswith("/"):
            parts = self._norm_parts(path)
            node = self.root
        else:
            parts = self._norm_parts(path)
            node = self.cwd

        # Если пустой путь (т.е. "/"), ничего не создаём
        if not parts:
            return

        # Проходим по всем частям, создаём директории при необходимости
        for i, part in enumerate(parts):
            is_last = (i == len(parts) - 1)
            if not node.is_dir:
                # не можем создать внутри файла
                raise ValueError(f"Cannot create {part} inside file {node.path()}")

            if part not in node.children:
                # если последний — создаём с нужным типом, иначе — директория
                node.children[part] = VFSNode(part, is_dir if is_last else True, parent=node)
            # если последний и это файл — установим content
            if is_last and not (node.children[part].is_dir):
                if content is not None:
                    node.children[part].content = content
            node = node.children[part]

    def _resolve(self, path):
        """
        Разрешает путь (абсолютный или относительный) и возвращает узел или None.
        Поддерживаются '.', '..'.
        """
        if path is None or path == "":
            return self.cwd

        # стартовая точка
        if path.startswith("/"):
            node = self.root
            parts = self._norm_parts(path)
        else:
            node = self.cwd
            parts = self._norm_parts(path)

        for part in parts:
            if part == ".":
                continue
            if part == "..":
                if node.parent is not None:
                    node = node.parent
                else:
                    # остаёмся в корне
                    node = self.root
                continue
            if not node.is_dir:
                return None
            if part not in node.children:
                return None
            node = node.children[part]
        return node

    def get_node(self, path):
        """Обёртка над _resolve; воспринимает None как cwd."""
        if path is None or path == "":
            return self.cwd
        if path == "/":
            return self.root
        return self._resolve(path)

    def list_dir(self, path=None):
        """Возвращает строку с элементами директории или сообщение об ошибке."""
        node = self.get_node(path)
        if not node:
            return f"No such directory: {path or self.get_cwd_path()}"
        if not node.is_dir:
            return f"{path or node.path()} is not a directory"
        # Отсортируем имена для стабильного вывода; не включаем пустые имена.
        names = sorted(node.children.keys())
        if not names:
            return ""
        return "  ".join(names)

    def change_dir(self, path):
        """Меняет текущую директорию; path может быть абсолютным или относительным."""
        if path is None or path == "":
            # переход в корень по умолчанию
            self.cwd = self.root
            return self.get_cwd_path()
        node = self.get_node(path)
        if not node:
            return f"No such directory: {path}"
        if not node.is_dir:
            return f"{path} is not a directory"
        self.cwd = node
        return self.get_cwd_path()

    def get_cwd_path(self):
        """Возвращает строковый путь текущей директории."""
        return self.cwd.path()

    def read_file(self, path):
        node = self.get_node(path)
        if not node:
            return f"No such file: {path}"
        if node.is_dir:
            return f"{path} is a directory"
        try:
            return base64.b64decode(node.content).decode('utf-8', errors='ignore') if self.is_base64(node.content) else node.content
        except Exception:
            return node.content

    @staticmethod
    def is_base64(s):
        try:
            # base64.b64decode часто не бросает исключение для произвольной строки,
            # поэтому проверим, что декодирование и обратное кодирование совпадает (более строгая проверка)
            if not s:
                return False
            decoded = base64.b64decode(s)
            return base64.b64encode(decoded).decode('utf-8') == s.replace("\n", "")
        except Exception:
            return False


# Глобальная переменная — экземпляр VFS
vfs = None

def load_vfs(vfs_file=None, output_func=print):
    """Загружает VFS из CSV-файла в память и возвращает экземпляр VirtualFileSystem."""
    global vfs

    if not vfs_file:
        output_func("load_vfs: no vfs_file provided, skipping load.")
        return None

    path_to_load = vfs_file

    if not os.path.exists(path_to_load):
        output_func(f"No VFS file found at {path_to_load}")
        return None

    vfs_instance = VirtualFileSystem()
    entries = 0
    try:
        with open(path_to_load, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                entries += 1
                path = row.get("path", "").strip()
                vtype = row.get("type", "").strip().lower()
                content = row.get("content", "")
                is_dir = (vtype == "dir")
                # не создавать узел для корня — корень уже есть
                if path == "/":
                    continue
                # При добавлении учитываем абсолютные пути (в CSV они начинаются с '/')
                vfs_instance.add_node(path, is_dir, content if not is_dir else None)
        vfs = vfs_instance
        output_func(f"VFS loaded successfully from {path_to_load} ({entries} entries)")
        return vfs_instance
    except Exception as e:
        output_func(f"Error loading VFS: {e}")
        return None
