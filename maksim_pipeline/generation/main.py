import os
from dotenv import load_dotenv
import yaml
from openai import OpenAI
import pandas as pd
from generator import Generator
from collector import CodeCollector


dataset = pd.read_csv('scenarios_with_funcs.csv')
dataset.index.name = "Index"

generator = Generator(system_prompt_file="system_prompt.txt")
collector = CodeCollector()
for index, row in dataset.iterrows():
    if index<=10:#для проверки
        try:
            generated_code = generator.process_scenario(row)
            
            collector.add_code(generated_code)
            
            print(f"Обработан сценарий {index + 1}/{len(dataset)}")
        except Exception as e:
            print(f"Ошибка при обработке сценария {index + 1}: {e}")

output_file = collector.save_to_file()
print(f"\nКод сохранен в файл: {output_file}")