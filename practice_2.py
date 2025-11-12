import argparse
import json
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

        # Обновление конфигурации пользовательскими значениями
        for key, value in user_config.items():
            if key in self.config:
                self.config[key] = value
            else:
                print(f"Предупреждение: неизвестный параметр '{key}' в конфигурации")

    def validate_config(self):
        """Валидация параметров конфигурации"""
        errors = []

        # Проверка обязательных параметров
        if not self.config['package_name']:
            errors.append("Не указано имя пакета (package_name)")

        if not self.config['repo_url']:
            errors.append("Не указан URL репозитория или путь к файлу (repo_url)")

        # Проверка максимальной глубины
        if not isinstance(self.config['max_depth'], int) or self.config['max_depth'] < 1:
            errors.append("max_depth должен быть целым числом больше 0")

        # Проверка булевых параметров
        for bool_param in ['test_mode', 'ascii_tree']:
            if not isinstance(self.config[bool_param], bool):
                errors.append(f"{bool_param} должен быть true или false")

        if errors:
            raise Exception("Ошибки конфигурации:\n- " + "\n- ".join(errors))

    def print_config(self):
        """Вывод всех параметров в формате ключ-значение"""
        print("Текущая конфигурация:")
        for key, value in self.config.items():
            print(f"  {key}: {value}")
        print("-" * 40)

    def command_line(self):
        """Обработка командной строки и конфигурации"""
        parser = argparse.ArgumentParser(
            description='CLI-приложение для анализа пакетов'
        )

        parser.add_argument('--config', '-c',
                            type=str,
                            required=True,
                            help='Путь к конфигурационному файлу JSON')

        args = parser.parse_args()

        try:
            # Загрузка и валидация конфигурации
            self.load_config(args.config)
            self.validate_config()

            # Вывод параметров (требование этапа 1)
            self.print_config()

            # Здесь будет основная логика анализа пакетов
            print("Конфигурация успешно загружена. Начинаем анализ...")

        except Exception as e:
            print(f"Ошибка: {e}")
            sys.exit(1)


if __name__ == "__main__":
    analyzer = PackageAnalyzer()
    analyzer.command_line()

# пример запуска: python practice_2.py --config config.json