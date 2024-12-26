import os
from dotenv import load_dotenv
from openai import OpenAI
import pandas as pd
import json

class Generator:
    def __init__(self, system_prompt_file=''):
        """
        Инициализация генератора с загрузкой системных промптов для разных режимов и API клиента.
        """
        load_dotenv()
        api_key = os.getenv("HF_API_KEY")
        if api_key is None:
            raise ValueError("API key not found in environment variables.")

        self.client = OpenAI(
            base_url="https://api-inference.huggingface.co/models/Qwen/Qwen2.5-Coder-32B-Instruct/v1/",
            api_key=api_key,
        )

        if system_prompt_file:
            with open(system_prompt_file, "r", encoding="utf-8") as f:
                self.system_prompt = f.read()
        else:
            self.system_prompt = ""

    def prepare_message(self, scene_text, funcs):
        """
        Подготовка сообщения в нужном формате.
        """
        return json.dumps({
            "scen": scene_text,
            "funcs": funcs
        }, ensure_ascii=False)

    def generate(self, user_message, max_tokens=1500):
        """
        Генерирует ответ на основе пользовательского сообщения и системного промпта.
        """
        if not user_message:
            raise ValueError("User message cannot be empty.")

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message}
        ]

        try:
            completion = self.client.chat.completions.create(
                model="Qwen2.5-Coder-32B-Instruct",
                messages=messages,
                temperature=0.7,  # Снижен для более предсказуемых ответов
                n=1,
                max_tokens=max_tokens,
            )
            
            return completion.choices[0].message.content

        except Exception as e:
            raise RuntimeError(f"Failed to generate response: {e}")

    def process_scenario(self, row):
        """
        Обработка одного сценария из датасета.
        
        :param row: Строка датафрейма с полями scene_text и funcs
        :return: Сгенерированный код функций
        """
        message = self.prepare_message(row['scene_text'], row['funcs'])
        return self.generate(message)