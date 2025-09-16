import shlex
import os
import re
import platform
vfs_name = 'home$'
exit_cmd = 'exit'

def expand_env_vars(command: str, env: dict = None) -> str:
    """
    Раскрывает переменные окружения в строке для UNIX-подобных и Windows систем.
    """
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
        if match.group(1) or match.group(2):
            var_name = match.group(1) or match.group(2)
            value = env.get(var_name, "")
            # Заменяем обратные слеши на прямые для совместимости с UNIX
            return value.replace('\\', '/')

        if match.group(3):
            var_name = match.group(3)
            for key, value in env.items():
                if key.upper() == var_name.upper():
                    return value.replace('\\', '/')
            return ""

        return match.group(0)

    def replace_tilde(match):
        value = env.get("HOME", "~")
        return value.replace('\\', '/')

    command = re.sub(r'%([^%]+)%', replace_var, command)
    command = re.sub(r'\$(\w+)|\$\{(\w+)\}', replace_var, command)
    command = re.sub(r'(?<!\\)~', replace_tilde, command)
    command = command.replace(r'\~', '~')

    return command


def act(command):
    if not command.strip():  # Пустая команда
        return None
    # Раскрываем переменные окружения
    expanded_command = expand_env_vars(command)
    parts = shlex.split(expanded_command)
    if parts[0] == exit_cmd:
        exit()
    if not parts:
        return None
    if parts[0] == 'ls':
        return " ".join(parts)
    elif parts[0] == 'cd':
        return " ".join(parts)
    else:
        return f'{command}: command not found'

if __name__ == "__main__":
    while True:
        command = input(vfs_name)
        result = act(command)
        if not result:
            break
        else:
            print(result)
