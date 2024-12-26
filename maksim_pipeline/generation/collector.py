import re
import os
from datetime import datetime

class CodeCollector:
    def __init__(self, output_dir="generated_code"):
        """
        Инициализация коллектора кода.
        
        :param output_dir: Директория для сохранения сгенерированных файлов
        """
        self.output_dir = output_dir
        self.collected_code = []
        self._ensure_output_dir()
        
    def _ensure_output_dir(self):
        """Создает директорию для вывода, если она не существует."""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
    
    def parse_code(self, generated_text):
        """
        Парсит сгенерированный текст и извлекает код функций.
        
        :param generated_text: Сгенерированный текст, содержащий код функций
        :return: Список найденных функций
        """

        function_pattern = r'(@tool\s*\ndef\s+[^@]+)'
        
        functions = re.findall(function_pattern, generated_text, re.DOTALL)
        
        cleaned_functions = [func.strip() for func in functions]
        
        return cleaned_functions
    
    def add_code(self, generated_text):
        """
        Добавляет сгенерированный код в коллекцию.
        
        :param generated_text: Сгенерированный текст с кодом
        """
        functions = self.parse_code(generated_text)
        self.collected_code.extend(functions)
    
    def save_to_file(self, filename=None):
        """
        Сохраняет собранный код в файл.
        
        :param filename: Имя файла (если не указано, генерируется автоматически)
        :return: Путь к сохраненному файлу
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"generated_functions_{timestamp}.py"
        
        filepath = os.path.join(self.output_dir, filename)
        
        header = """# Generated Functions
from typing import Any
from langchain.tools import tool

"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(header)
            for func in self.collected_code:
                f.write(func + '\n\n')
        
        return filepath

    def clear(self):
        """Очищает коллекцию собранного кода."""
        self.collected_code.clear()