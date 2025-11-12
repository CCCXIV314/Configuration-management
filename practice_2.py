import argparse
import json
import urllib.request
import re
import os
import sys


class PackageAnalyzer:
    def __init__(self):
        self.config = {
            'package_name': '',
            'repo_url': '',
            'test_mode': False,
            'ascii_tree': True,
            'max_depth': 5
        }

    def load_config(self, config_path):
        """Загрузка конфигурации из JSON-файла"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
        except FileNotFoundError:
            raise Exception(f"Конфигурационный файл не найден: {config_path}")
        except json.JSONDecodeError:
            raise Exception(f"Ошибка парсинга JSON в файле: {config_path}")

        for key, value in user_config.items():
            if key in self.config:
                self.config[key] = value

    def validate_config(self):
        """Валидация параметров конфигурации"""
        errors = []

        if not self.config['package_name']:
            errors.append("Не указано имя пакета")
        if not self.config['repo_url']:
            errors.append("Не указан URL репозитория или путь к файлу")

        if errors:
            raise Exception("Ошибки конфигурации:\n- " + "\n- ".join(errors))

    def get_dependencies(self):
        """Получение прямых зависимостей пакета"""
        package_name = self.config['package_name']

        if self.config['test_mode']:
            # Режим тестового репозитория - работа с локальным файлом
            dependencies = self.get_dependencies_from_file()
        else:
            # Режим онлайн - работа с PyPI
            dependencies = self.get_dependencies_from_pypi(package_name)

        # Вывод прямых зависимостей (требование этапа 2)
        print("Прямые зависимости пакета '{}':".format(package_name))
        if dependencies:
            for dep in dependencies:
                print(f"  - {dep}")
        else:
            print("  Зависимости не найдены")

        return dependencies

    def get_dependencies_from_pypi(self, package_name):
        """Получение зависимостей из PyPI"""
        try:
            # Формируем URL на основе конфигурации
            if self.config['repo_url'].startswith(('http://', 'https://')):
                url = f"{self.config['repo_url']}{package_name}/json"
            else:
                url = f"https://{self.config['repo_url']}{package_name}/json"

            with urllib.request.urlopen(url) as response:
                data = json.loads(response.read().decode('utf-8'))

            return self.parse_dependencies(data)

        except Exception as e:
            print(f"Ошибка при получении зависимостей: {e}")
            return []

    def get_dependencies_from_file(self):
        """Получение зависимостей из тестового файла"""
        try:
            with open(self.config['repo_url'], 'r', encoding='utf-8') as f:
                data = json.load(f)
            return self.parse_dependencies(data)
        except Exception as e:
            print(f"Ошибка при чтении тестового файла: {e}")
            return []

    def parse_dependencies(self, package_data):
        """Парсинг зависимостей из данных пакета"""
        dependencies = []

        if 'info' in package_data and 'requires_dist' in package_data['info']:
            requires_dist = package_data['info']['requires_dist']

            if requires_dist:
                pattern = r"^([a-zA-Z\d_-]+)\s*"
                for dep in requires_dist:
                    # Игнорируем зависимости с условиями (extra)
                    if 'extra' in dep:
                        continue

                    # Извлекаем имя пакета
                    match = re.match(pattern, dep.split(';')[0].strip())
                    if match:
                        package_name = match.group(1)
                        if package_name not in dependencies:
                            dependencies.append(package_name)

        return dependencies

    def command_line(self):
        """Обработка командной строки"""
        parser = argparse.ArgumentParser(
            description='CLI-приложение для анализа зависимостей пакетов'
        )

        parser.add_argument('--config', '-c',
                            type=str,
                            required=True,
                            help='Путь к конфигурационному файлу JSON')

        args = parser.parse_args()

        try:
            # Загрузка конфигурации
            self.load_config(args.config)
            self.validate_config()

            # Вывод конфигурации (этап 1)
            print("Конфигурация:")
            for key, value in self.config.items():
                print(f"  {key}: {value}")
            print("-" * 40)

            # Получение и вывод зависимостей (этап 2)
            self.get_dependencies()

        except Exception as e:
            print(f"Ошибка: {e}")
            sys.exit(1)


if __name__ == "__main__":
    analyzer = PackageAnalyzer()
    analyzer.command_line()

# пример запуска: python practice_2.py --config config.json