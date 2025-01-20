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
def assess_financial_status(income: float, expenses: float, credit_history: str):
    """Оценивает финансовое состояние клиента на основе доходов, расходов и кредитной истории."""
    # Логика для оценки финансового состояния
    return f"Финансовое состояние оценено. Доходы: {income}, Расходы: {expenses}, Кредитная история: {credit_history}"

@tool
def propose_loan_terms(income: float, credit_score: int):
    """Предлагает варианты условий кредита на основе доходов и кредитного рейтинга."""
    # Логика для предложения условий кредита
    return f"Предлагаемые условия кредита для клиента с доходом {income} и кредитным рейтингом {credit_score}."

@tool
def confirm_client_agreement(agreement_details: str):
    """Согласование с клиентом условий кредита."""
    # Логика для согласования условий кредита
    return f"Условия кредита согласованы. Детали: {agreement_details}"
@tool
def fetch_current_tariffs(tariffs: list):
    """Получение актуальных тарифов на мобильный банкинг."""
    # Логика для получения тарифов, например, через API
    return f"Актуальные тарифы: {tariffs}"

@tool
def compare_tariffs_by_category(categories: dict):
    """Сравнение предложенных тарифов по категориям."""
    # Логика для сравнения тарифов по категориям
    return f"Сравнение тарифов по категориям: {categories}"

@tool
def determine_best_tariff(best_tariff: str):
    """Определение наиболее подходящего тарифа."""
    # Логика для определения лучшего тарифа
    return f"Наиболее подходящий тариф: {best_tariff}"

@tool
def activate_tariff(tariff_name: str):
    """Оформление подключения к выбранному тарифу."""
    # Логика для оформления подключения к тарифу
    return f"Тариф {tariff_name} успешно активирован"
    
    
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

