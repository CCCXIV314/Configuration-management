import os
import csv
import datetime

class CSVLogger:
    """Логгер в формате CSV"""
    def __init__(self, log_file):
        self.log_file = log_file
        # Создаем файл с заголовками, если он не существует
        if not os.path.exists(log_file):
            with open(log_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp', 'command', 'error_message'])

    def log(self, command, error_message=""):
        """Запись события в лог"""
        with open(self.log_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.datetime.now().isoformat(),
                command,
                error_message
            ])