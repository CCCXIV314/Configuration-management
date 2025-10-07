import shlex
import os
import re
import argparse
from CSVlogger import CSVLogger
import sys

# Глобальные переменные для конфигурации
vfs_name = 'home$'
exit_cmd = 'exit'
vfs_path = None
log_path = None
stscript_path = None
logger = None



def init_config(args_list=None, output_func=print):
    """Инициализация конфигурации из аргументов командной строки"""
    global vfs_path, log_path, stscript_path, logger

    parser = argparse.ArgumentParser(description='VFS Emulator')
    parser.add_argument('--vfs-path', help='Path to VFS physical location')
    parser.add_argument('--log-path', help='Path to log file')
    parser.add_argument('--stscript-path', help='Path to startup script')

    # Важно: передаём args_list в parse_args — если args_list=None, argparse использует sys.argv
    args = parser.parse_args(args_list)

    # Устанавливаем значения по умолчанию, если не указаны
    vfs_path = args.vfs_path or os.getcwd()
    log_path = args.log_path or 'emu_log.csv'
    stscript_path = args.stscript_path or 'start_script.txt'

    # Вывод отладочной информации через переданную функцию (print или GUI printer)
    output_func(f"Debug: VFS Path = {vfs_path}")
    output_func(f"Debug: Log Path = {log_path}")
    output_func(f"Debug: Startup Script Path = {stscript_path}")

    # Инициализация логгера
    logger = CSVLogger(log_path)


def find_default_start_script():
    """Если --stscript-path не задан, ищем start_script.txt рядом с файлом emu.py"""
    global stscript_path
    if stscript_path:
        return  # уже задано через args
    # папка, где лежит сам модуль emu.py
    module_dir = os.path.dirname(os.path.abspath(__file__))
    candidate = os.path.join(module_dir, "start_script.txt")
    if os.path.exists(candidate):
        # не меняем предыдущий debug-вывод — он уже показал None, но всё же выполним скрипт
        stscript_path = candidate

def expand_env_vars(command: str, env: dict = None) -> str:
    if env is None:
        env = dict(os.environ)

    # Нормализуем переменные окружения: заменяем обратные слеши на прямые
    normalized_env = {}
    for key, value in env.items():
        normalized_env[key] = value.replace('\\', '/')

    env = normalized_env

    if 'HOME' not in env and 'USERPROFILE' in env:
        env['HOME'] = env['USERPROFILE']

    def replace_var(match):
        # group(1) — %VAR% via first regex, group(2) or group(3) for $VAR and ${VAR}
        if match.group(1):  # %VAR%
            var_name = match.group(1)
            return env.get(var_name, "").replace('\\', '/')
        if match.group(2) or match.group(3):  # $VAR or ${VAR}
            var_name = match.group(2) or match.group(3)
            return env.get(var_name, "").replace('\\', '/')
        return match.group(0)

    def replace_tilde(match):
        value = env.get("HOME", "~")
        return value.replace('\\', '/')

    command = re.sub(r'%([^%]+)%', replace_var, command)
    command = re.sub(r'\$(\w+)|\$\{(\w+)\}', replace_var, command)
    command = re.sub(r'(?<!\\)~', replace_tilde, command)
    command = command.replace(r'\~', '~')

    return command


def execute_startup_script(output_func=print):
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


def set_parameter(args):
    """Обработка команды set parameter"""
    global vfs_path, log_path, stscript_path

    if len(args) < 2:
        return "Usage: set parameter --<parameter-name> <value>"

    param_name = args[0]
    param_value = args[1]

    if param_name == "--vfs-path":
        vfs_path = param_value
        vfs_path = vfs_path.replace('\\', '/')
        return f"VFS path set to: {vfs_path}"
    elif param_name == "--log-path":
        log_path = param_value
        logger = CSVLogger(log_path)
        log_path = log_path.replace('\\', '/')
        return f"Log path set to: {log_path}"
    elif param_name == "--stscript-path":
        stscript_path = param_value
        stscript_path = stscript_path.replace('\\', '/')
        return f"Startup script path set to: {stscript_path}"
    else:
        return f"Unknown parameter: {param_name}"

def act(command):
    """Обработчик команд эмулятора. Возвращает строку результата или сообщение об ошибке."""
    global logger, log_path

    if command is None:
        return None

    command_stripped = command.strip()
    if not command_stripped:  # Пустая команда
        return None

    # Если логгер не инициализирован (вызов из GUI без init_config), создаём дефолтный.
    if logger is None:
        logger = CSVLogger(log_path or 'emu_log.csv')

    # Если введена **только** переменная окружения, вернуть её значение напрямую
    # Поддерживается: $VAR, ${VAR}, %VAR%, ~
    if re.fullmatch(r'\$[A-Za-z_]\w*|\$\{[A-Za-z_]\w*\}|%[^%]+%|~', command_stripped):
        expanded = expand_env_vars(command_stripped)
        logger.log(command_stripped, "")
        return expanded

    # Раскрываем переменные окружения в любой части команды
    expanded_command = expand_env_vars(command_stripped)
    # Разбираем команду
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
        # Для консольного варианта можно завершать процесс; в GUI act('exit') просто вернёт None
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

    # Простейшие команды: ls, cd — имитируем поведение (возвращаем то, что ввели)
    if parts[0] == 'ls':
        logger.log(command_stripped, "")
        return " ".join(parts)
    elif parts[0] == 'cd':
        logger.log(command_stripped, "")
        return " ".join(parts)
    else:
        error_msg = f'{command_stripped}: command not found'
        logger.log(command_stripped, error_msg)
        return error_msg


if __name__ == "__main__":

    # Инициализация конфигурации (CLI)
    init_config()

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



