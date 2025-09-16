import os


def replace_match(match):
    var_name = match.group(1)
    # Получаем значение переменной окружения (регистронезависимо)
    return os.environ.get(var_name.upper(), match.group(0))


