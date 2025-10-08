import argparse
import re
from CSVlogger import CSVLogger
from vfs import VirtualFileSystem, load_vfs
import os

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

    if os.path.isdir(vfs_path):
        vfs_csv = os.path.join(vfs_path, 'vfs.csv')
    else:
        vfs_csv = vfs_path

    if os.path.exists(vfs_csv):
        load_vfs(vfs_csv, output_func)
    else:
        output_func(f"No VFS file found at {vfs_csv}")

def find_default_start_script():
    """Если --stscript-path не задан, ищем start_script.txt рядом с файлом emu.py"""
    global stscript_path
    if stscript_path:
        return  # уже задано через args
    # папка, где лежит сам модуль emu.py
    module_dir = os.path.dirname(os.path.abspath(__file__))
    candidate = os.path.join(module_dir, "start_script.txt")
    if os.path.exists(candidate):
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
        if match.group(1):
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