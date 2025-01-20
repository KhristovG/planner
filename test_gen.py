import warnings
warnings.filterwarnings("ignore")
from langchain_gigachat import GigaChat
from langgraph.graph import MessagesState
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import START, StateGraph, END
from langgraph.prebuilt import tools_condition, ToolNode
from langchain_core.tools import tool
from IPython.display import Image, display
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from typing import Annotated, List, Tuple, Union, Literal, Dict
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
import os
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever
from langchain_community.document_loaders.csv_loader import CSVLoader
import pandas as pd
import re
import ast
from langgraph.prebuilt import create_react_agent

from langchain_community.tools.tavily_search import TavilySearchResults
# Загружаем переменные окружения из .env файла
load_dotenv()

# # Получаем API-ключ из переменной окружения
creds = os.getenv('credentials')
token = os.getenv('OPENAI_API_KEY')

from tabulate import tabulate


# llm = ChatOpenAI(
#     model="gpt-4o-mini", temperature=0.1
# )

llm = GigaChat(
        credentials = creds,
        verify_ssl_certs=False,
        scope = 'GIGACHAT_API_CORP',
        temperature=0.1,
        # model="GigaChat",
        model="GigaChat-Max",
        
        # model="GigaChat-Max-preview",
        # base_url="https://gigachat-preview.devices.sberbank.ru/api/v1/"       
    )


choose_question_rag_prompt = """
Роль:
Ты — агент, выбирающий наиболее подходящий вопрос к вопросу пользователя.

Задание:
1. Проанализируй предоставленные вопросы и вопрос пользователя.
2. Верни наиболее похожий вопрос, либо ответь что похожего вопроса нет.

Предоставленные вопросы:
{context}

Вопрос пользователя:
{question}

Твоя задача — вернуть из предоставленных вопросов вопрос наиболее похожий на вопрос пользоватeля, либо сообщить об отсутствии такого вопроса (верни 'no'). В ответе должен быть только текст наиболее подходящего вопроса.
Внимание: Удостоверься, что пунктуация возвращаемого тобой вопроса совпадает с той, которая была в момент предоставления вопросов (если в предоставленном вопросе в конце не было знака вопроса, то его добавлять не нужно).
"""

choose_question_rag_template = ChatPromptTemplate.from_template(choose_question_rag_prompt)

question_choose_agent = choose_question_rag_template | llm


def get_embeddings():
    model_name = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
    model_kwargs = {'device': 'cpu'}
    encode_kwargs = {'normalize_embeddings': False}
    embedding = HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs=model_kwargs,
        encode_kwargs=encode_kwargs
        )
    return embedding

def prep_bd():
    file_path = '/home/maksim-litvninov/Documents/'
    vector_store_loaded = FAISS.load_local(folder_path=file_path, embeddings=get_embeddings(), allow_dangerous_deserialization= True)
    loaded_retriever = vector_store_loaded.as_retriever(search_kwargs={'k': 3}, search_type="mmr")
    return loaded_retriever
@tool
def check_cancellation_conditions(transaction_id: str):
    """Проверяет условия для отмены транзакции."""
    # Логика для проверки условий отмены транзакции
    return f"Условия для отмены транзакции {transaction_id} проверены."

@tool
def execute_transaction_cancellation(transaction_id: str):
    """Выполняет отмену транзакции."""
    # Логика для выполнения отмены транзакции
    return f"Транзакция {transaction_id} отменена."

@tool
def confirm_cancellation(transaction_id: str):
    """Подтверждает успешную отмену транзакции."""
    # Логика для подтверждения успешной отмены транзакции
    return f"Отмена транзакции {transaction_id} подтверждена."
@tool
def analyze_suspicious_transactions(transactions: list):
    """Анализирует список транзакций на наличие подозрительных операций."""
    # Логика для анализа транзакций
    suspicious_transactions = [t for t in transactions if t['amount'] > 10000 or t['location'] == 'Unknown']
    return suspicious_transactions

@tool
def block_suspicious_transactions(transaction_ids: list):
    """Блокирует подозрительные транзакции на основе их идентификаторов."""
    # Логика для блокировки транзакций
    return f"Транзакции с ID {transaction_ids} заблокированы."

@tool
def restore_account_access(reason: str):
    """Восстанавливает доступ к счету по указанной причине."""
    # Логика для восстановления доступа к счету
    return f"Доступ к счету восстановлен по причине: {reason}."
    
    
@tool
def factual_questions(user_question: str) -> str:
    '''Use search_tool when answering factual questions.'''
    search_tool = TavilySearchResults(
        max_results=5,
    )
    return search_tool.invoke(user_question)

@tool
def sberbank_question(bank_question: str) -> str:
    '''Answer questions about Sberbank products and services.'''
    pf = pd.read_csv('FAQ.csv')

    class StateRAG(TypedDict):
        question: str
        context: List[Document]
        answer: str

    def retrieve_question(state: StateRAG):
        retrieved_docs = prep_bd().invoke(state["question"])
        return {"context": retrieved_docs}

    def map_questions_and_answer(state: StateRAG):
        docs_content = "".join(doc.page_content for doc in state["context"])
        question = question_choose_agent.invoke({
            "context": docs_content,
            "question": state["question"]
        })

        if question.content.lower() not in ['no', "'no'"]:
            q = pf.loc[pf['Вопрос'] == question.content[8:], 'Ответ'].values[0]
            return {'answer': q}
        return {"answer": 'No answer available for your question'}

    graph_builder = StateGraph(StateRAG).add_sequence([
        retrieve_question,
        map_questions_and_answer
    ])
    graph_builder.add_edge(START, "retrieve_question")
    graph = graph_builder.compile()

    return f'{graph.invoke({"question": bank_question})["answer"]}'

def extract_tool_functions(filename):
    """Извлекает названия функций, декорированных @tool, из файла."""
    with open(filename, "r") as file:
        node = ast.parse(file.read(), filename=filename)

    tool_functions = []
    for n in node.body:
        if isinstance(n, ast.FunctionDef):
            for decorator in n.decorator_list:
                if isinstance(decorator, ast.Name) and decorator.id == 'tool':
                    tool_functions.append(n.name)
                    break

    return tool_functions

tool_functions = extract_tool_functions(__file__)

all_tools = [globals()[name] for name in tool_functions]

print("tools которые мы забиндим в ллмку:", [tool_.name for tool_ in all_tools])

tool_node = ToolNode(all_tools)
memory = MemorySaver()

slovar = {
    'Название сценария': [
        '''Отмена транзакции''',
        '''Защита счета от мошенничества''',
    ],
    'Условия входа': [
        '''Запрос пользователя связан с одной из перечисленных тем: 
1) отмена транзакции
2) возврат средств''',
        '''Запрос пользователя связан с одной из перечисленных тем:
1) подозрительная активность на счете
2) уведомление о возможном мошенничестве''',
    ],
    'Описание сценария': [
        '''Получение информации о транзакции. Проверка условий отмены. - Используй функцию check_cancellation_conditions(). Выполнение отмены транзакции. - Используй функцию execute_transaction_cancellation(). Подтверждение успешной отмены. - Используй функцию confirm_cancellation().''',
        '''Проверка активности транзакций. Анализ подозрительных операций. - Используй функцию analyze_suspicious_transactions(). Уведомление клиента о подозрительных действиях. Блокировка подозрительных транзакций. - Используй функцию block_suspicious_transactions(). Восстановление доступа к счету. - Функция restore_account_access().''',
    ],
    'Справочная информация': [
        '''
        Справочной информации нет для текущего сценария, используйте функции check_cancellation_conditions(), execute_transaction_cancellation(), confirm_cancellation().
        ''',
        '''
        Справочной информации нет для текущего сценария, используйте функции analyze_suspicious_transactions(), block_suspicious_transactions(), restore_account_access().
        ''',
    ],
}

df = pd.DataFrame(slovar)
print(df)