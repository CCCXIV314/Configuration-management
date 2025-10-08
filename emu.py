import shlex
from vfs import load_vfs
from config import *
import sys
import fnmatch

# Глобальные переменные
vfs = None
vfs_name = 'home$'
exit_cmd = 'exit'

def execute_startup_script(output_func=print):
    from config import stscript_path
    """Выполнение стартового скрипта. output_func — куда писать вывод (print или GUI printer)."""
    if not stscript_path or not os.path.exists(stscript_path):
        return

    output_func(f"Executing startup script: {stscript_path}")

    try:
        with open(stscript_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                command = line.strip()
                if not command or command.startswith('#'):
                    continue

                # Выводим команду как если бы её ввел пользователь
                output_func(f"{vfs_name} {command}")

                # Выполняем команду
                result = act(command)

                # Выводим результат (если есть)
                if result:
                    output_func(result)

                # Если команда вернула ошибку - останавливаем выполнение
                if result and "command not found" in result:
                    output_func(f"Script stopped at line {line_num} due to error")
                    break
    except Exception as e:
        output_func(f"Error executing startup script: {e}")

def _find_matches(start_node, pattern):
    """Рекурсивно ищет узлы, соответствующие шаблону. Возвращает список полных путей."""
    matches = []

    # если start_node сам файл/директория совпадает — учитываем
    if start_node is None:
        return matches

    # node itself
    if start_node.name and (fnmatch.fnmatch(start_node.name, pattern) or pattern in start_node.name):
        matches.append(start_node.path())

    # если это директория — ищем в детях
    if start_node.is_dir:
        for child_name, child in start_node.children.items():
            # рекурсивный проход
            matches.extend(_find_matches(child, pattern))
    return matches

def act(command):

    global logger, log_path, vfs

    if command is None:
        return None

    command_stripped = command.strip()
    if not command_stripped:  # Пустая команда
        return None

    # Если логгер не инициализирован (вызов из GUI без init_config), создаём дефолтный.
    if logger is None:
        logger = CSVLogger(log_path or 'emu_log.csv')

    # Поддерживается: $VAR, ${VAR}, %VAR%, ~
    if re.fullmatch(r'\$[A-Za-z_]\w*|\$\{[A-Za-z_]\w*\}|%[^%]+%|~', command_stripped):
        expanded = expand_env_vars(command_stripped)
        logger.log(command_stripped, "")
        return expanded

    # Раскрываем переменные окружения в любой части команды
    expanded_command = expand_env_vars(command_stripped)

    try:
        parts = shlex.split(expanded_command)
    except Exception as e:
        error_msg = f'Failed to parse command: {e}'
        logger.log(command_stripped, error_msg)
        return error_msg

    if not parts:
        return None

    if parts[0] == exit_cmd:
        logger.log(command_stripped, "")
        try:
            sys.exit(0)
        except SystemExit:
            return None

    # Обработка команды set parameter
    if parts[0] == 'set' and len(parts) > 1 and parts[1] == 'parameter':
        result = set_parameter(parts[2:])
        # set_parameter может вернуть сообщение об ошибке или о результате
        # Логируем и возвращаем
        logger.log(command_stripped, "" if "Unknown parameter" not in (result or "") and "Usage:" not in (result or "") else (result or ""))
        return result

    if parts[0] == 'ls':
        logger.log(command_stripped, "")
        if vfs:
            return vfs.list_dir(parts[1] if len(parts) > 1 else None)
        return "VFS not loaded"

    if parts[0] == 'cd':
        logger.log(command_stripped, "")
        if vfs:
            return vfs.change_dir(parts[1] if len(parts) > 1 else "/")
        return "VFS not loaded"
    # else:
    #     error_msg = f'{command_stripped}: command not found'
    #     logger.log(command_stripped, error_msg)
    #     return error_msg

    # find
    if parts[0] == 'find':
        logger.log(command_stripped, "")
        if not vfs:
            return "VFS not loaded"
        # Usage:
        #   find <pattern>           -> search from cwd
        #   find <start> <pattern>   -> search from <start>
        if len(parts) == 1:
            return "Usage: find <pattern>  or  find <start> <pattern>"
        if len(parts) == 2:
            start_path = None
            pattern = parts[1]
        else:
            # len >=3: first arg after 'find' is start, second is pattern; ignore extra args
            start_path = parts[1]
            pattern = parts[2]

        # resolve start node
        start_node = vfs.get_node(start_path) if start_path else vfs.get_node(None)
        if not start_node:
            return f"No such directory: {start_path or vfs.get_cwd_path()}"
        # if start_node is a file and matches -> return it; otherwise traverse
        matches = []
        # if pattern looks like a simple substring (no wildcards) we still use fnmatch for consistency
        matches = _find_matches(start_node, pattern)
        if not matches:
            return "(no matches)"
        # Return sorted unique list
        uniq = sorted(dict.fromkeys(matches))
        return "\n".join(uniq)

    # cat
    if parts[0] == 'cat':
        logger.log(command_stripped, "")
        if not vfs:
            return "VFS not loaded"
        if len(parts) < 2:
            return "Usage: cat <file>"
        path = parts[1]
        # Try reading the file via vfs.read_file
        result = vfs.read_file(path)
        # If vfs.read_file returns error string (starting with "No such" or "is a directory"), treat as error
        if isinstance(result, str) and (result.startswith("No such") or result.endswith("is a directory")):
            logger.log(command_stripped, result)
            return result
        # otherwise log success (empty error message)
        logger.log(command_stripped, "")
        return result

    # unknown command
    error_msg = f'{command_stripped}: command not found'
    logger.log(command_stripped, error_msg)
    return error_msg


if __name__ == "__main__":

    # Инициализация конфигурации (CLI)
    init_config()

    # Синхронизация: берём экземпляр vfs, который создался в модуле vfs (через load_vfs в config)
    import vfs as vfs_module

    vfs = getattr(vfs_module, "vfs", None)


    # Если рядом с emu.py есть start_script.txt — назначим его в stscript_path
    find_default_start_script()

    # Выполнение стартового скрипта (CLI)
    execute_startup_script()

    # CLI loop
    while True:
        try:
            command = input(vfs_name)
        except (EOFError, KeyboardInterrupt):
            print()
            break
        result = act(command)
        if not result:
            break
        else:
            print(result)



