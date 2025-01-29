# Импорты
from langchain_gigachat import GigaChat
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import START, StateGraph, END
from langgraph.prebuilt import tools_condition, ToolNode
from IPython.display import Image, display
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.prompts import ChatPromptTemplate
from typing import Annotated, List, Tuple, Union, Literal, Dict, Optional
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode
# from langchain_community.tools.tavily_search import TavilySearchResults
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
# from langchain_core.runnables.config import RunnableConfig
from langgraph.types import Command
import os
from dotenv import load_dotenv
import pandas as pd

from prompts_planer import prompts_pl
from graph_help_func import get_tool_parameters, get_next_unfinished_item, execute_item, get_curr_plan_id, get_status, mark_item_completed, update_plan_status, display_dataframe_pretty, _print_event, extract_relevant_messages
# Загружаем переменные окружения из .env файла
load_dotenv()

#  Получаем API-ключ из переменной окружения
creds = os.getenv('credentials')

from tabulate import tabulate
# llm = ChatOpenAI(
#     model="gpt-4o-mini", temperature=0.1
# )

llm = GigaChat(
        credentials = creds,
        verify_ssl_certs=False,
        scope = 'GIGACHAT_API_CORP',
        temperature=0.1,
        profanity_check = False,
        model="GigaChat-Max",
    )

data = {
    'Название сценария': ['Потеря/сломалась банковская карта','Сценарий определения погоды'],
    'Условия входа': [
        """Запрос пользователя связан с одной из перечисленных тем:
        1) Потеря карты 
        2) Сломалась карта
        Это обязательные уловия для входа в сценарий, если карта НЕ утрачена и НЕ сломана, то в этот сценарий входить нельзя.
        """,
        """Запрос пользователя связан с одной из перечисленных тем:
        1) погода
        2) осадки
        3) атмосферное давление""",
    ],
    'Описание сценария': ["""Сценарий потери банковской карты:
1) Этап подготовки:
Сообщение вводной инфы сценария о том, что карту надо заблокировать и перевыпустить
2) Этап блокировки карты:
Запуск функции getActiveUserCards()
Предоставление выбора среди карт пользователю
Запуск функции wf:blockcard()
3) Этап заказа моментальной карты:
Предложение заказать новую моментальную карту
Предложение выбрать способ доставки в офис сбера или курьером
Запрос у пользователя адреса доставки
Запуск функции getAddress()
Запуск функции getUserProfile()
Запуск функции checkDeliveryAvailability()
Запуск функции getDeliverySlots()
Предоставление пользователю выбора даты доставки
Предоставление пользователю выбора варианта доставки: по клику или ко времени
Предоставление пользователю выбора времени доставки
Запуск функции wf:physical()
4) Обработка результата всего плана, возврат в общий контекст""" 
        ,
        """
        В рамках сценария определения погоды сперва необходимо определить в какой именно местности необходимо уточнить погоду.
        Если Пользователь сразу назвал необходимое место (например: "Скажи погоду в Москве") то определи с помощью функции factual_questions() погоду в названной пользователем местности.
        В случае, если не удается однозначно определить необходимую местность, то доуточни у пользователя, а затем вызови функцию factual_questions() для текущей местности.
        """
    ],
}
df = pd.DataFrame(data)

@tool
def getActiveUserCards(cards:str) -> str:
    """Возвращает список активных карт пользователя, которые можно заблокировать"""
    cards_name = ['МИР***1234', 'VISA***2345','MASTERCARD***3456']
    return f'Список доступных карт: {cards_name}'

@tool
def blockcard(cardLinkId: str)-> str:
    """Запускает многошаговый процесс блокировки карты с помощью агента WF"""
    return f"Карта {cardLinkId} успешно заблокирована."

@tool
def getAddress(q: str, fields:str, key:str)-> str:
    """Возвращает информацию по введенному пользователем адресу(ам) из 2GIS"""
    return f"Адрес"

@tool
def getUserProfile()-> str:
    """Возвращает данные о профиле клиента"""
    return f"Данные о профиле клиента"

@tool
def checkDeliveryAvailability(requestChannel: str, tariffCode:str, tariff:str, issueType:str, typeProduct:str)-> str:
    """Проверяет возможность доставки по указанному адресу для конкретного пользователя"""
    return f"Доставка по адресу возможна"

@tool
def getDeliverySlots(clientSegment: str, codeWay4:str, tariff:str, customDesignCode:str, additionalInfo:str, requestChannel:str, issueType:str, typeProduct:str, zoneCode: str)-> str:
    """Возвращает временные слоты для доставки карты: дата доставки, вариант доставки (ко времени или по клику), временные слоты"""
    return f"getDeliverySlots"

@tool
def physical(deliveryType: str, zoneCode:str, layerId:str, longitude:str, latitude:str, apartmentid: str, entranceid:str, type:str, street:str, slotId:str, city:str, slotid:str, day:str, supplierCode:str)-> str:
    """Запускает многошаговый процесс заказа доставки пластика с помощью агента WF"""
    return f"physical"

tools = [getActiveUserCards, blockcard, getAddress, getUserProfile, checkDeliveryAvailability, getDeliverySlots, physical]
tool_node = ToolNode(tools)
memory = MemorySaver()

# планировщики сценарный и динамический (чисто на функциях)

def plan_scenar(scen,mess):
    plan_tmp = prompts_pl['plan_tmp']
    scen_prompt = ChatPromptTemplate.from_template(plan_tmp)
    model = llm.bind_functions(tools)
    chain = scen_prompt | model#.with_structured_output(Plan)
    return chain.invoke({'scenario':scen, 'messages':mess})

# динамический планер
def plan_dinamic(mess, plan_atom):
    plan_atom = prompts_pl['plan_atom']
    atom_prompt = ChatPromptTemplate.from_template(plan_atom)
    model = llm.bind_functions(tools)#, parallel_tool_calls=False
    chain = atom_prompt | model
    return chain.invoke({'messages':mess})

def add_generated_plan(plan_text, start_mes, completed_items=None, plan_status="start"): # возможно эта функция не нужна, потом через стейт add
    global CACHE_DF

    new_id = CACHE_DF['plan_id'].max() + 1 if not CACHE_DF.empty else 1

    new_row = {
        'plan_id': new_id,
        'plan_text': plan_text,
        'plan_status': plan_status,
        'completed_items': completed_items,
        'start_mes':start_mes,
        'summary':summary.invoke({plan_text}).content
    }

    CACHE_DF = pd.concat([CACHE_DF, pd.DataFrame([new_row])], ignore_index=True)
# Graders
#грейдер соблюдения условий входа

# class GradeEnter(BaseModel):
#     """Соблюдены ли условия входа в сценарий"""

#     name: str = Field(
#         ...,
#         description="Соблюдены ли условия входа в сценарий, если соблюдены верни название сценария, если не соблюдены верни 'no'",
#     )
planner_grade_scen_prompt = ChatPromptTemplate.from_template(prompts_pl['grader_scen_prompt'])
planner_scen_grader = planner_grade_scen_prompt | llm#.with_structured_output(GradeEnter, include_raw=True)

#grader old_plans
class PlanEvaluator(BaseModel):
    """Проверка, удовлетворяет ли запросу пользователя один из существующих планов"""

    result: str = Field(
        ...,
        description="Верни 'NO', если подходящего плана нет, или 'id плана', если один из планов подходит.",
    )
check_plan_from_cache_prompt = ChatPromptTemplate.from_template(prompts_pl['check_plan_from_cache_template'])
check_plan_grader = check_plan_from_cache_prompt | llm.with_structured_output(PlanEvaluator)

# grader summary
summary_prompt = ChatPromptTemplate.from_template(prompts_pl['summary_prompt_template'])
summary = summary_prompt | llm


# Экзекьютор и чатер
# экзекьютор 
from langchain_core.runnables import RunnablePassthrough

def get_executor(plan):
    executor_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", f"""Ты — агент-исполнитель. Твоя задача — выполнить план действий, который ты получил от агента-планировщика. Следуй по плану, при этом уточняй информацию или предпринимай дополнительные шаги, если это необходимо.
    План:
    {plan}
    Пожалуйста, начни выполнение задач, следуя указанному плану. Функции можно использовать только если они упоминаются в пункте плана. После получения tool_message не забудь учесть его при формировании ответа пользователю.
    Если функции не использовались просто верни пункт плана.
    """),
            ("human", "{input}"),
        ]
    )
    model = llm
    model = model.bind_tools(tools)#, parallel_tool_calls=False
    chain = {"input": RunnablePassthrough()} | executor_prompt | model
    return chain

# chater

chat_agent_prompt = ChatPromptTemplate.from_template(prompts_pl['chat_agent_prompt_templ'])
chat_agent = chat_agent_prompt | llm


# Сам граф

class ComplexState(TypedDict):
    plan: List[str]
    messages: Annotated[list[HumanMessage | AIMessage | ToolMessage], add_messages]
    vremya_dengi: dict[str,str]
    df: dict
    user_mess: str
    response_mock: str
    item: str

# Define the function that determines whether to continue or not. Вызывать тулзу или нет. Вроде есть готовое решение tool_conditions или как-то так
def should_continue(state):
    messages = state["messages"]
    last_message = messages[-1]
    # If there is no function call, then we finish
    if not last_message.tool_calls:
        return "end"
    # Otherwise if there is, we continue
    else:
        return "continue"

def node_old_plan_exist(state) -> Command[Literal["conditions_and_plans", "executor"]]:
    user_mess = state['messages'][-1].content
    plan = state.get("plan")
    plans_dict = {f"plan_id:{row['plan_id']}, plan_text: {row['plan_text']}" for _, row in CACHE_DF.iterrows()}
    
    # print(f" node_old_plan_exist plans_dict{plans_dict}")

    old_plan_score = check_plan_grader.invoke({"plans_dict":str(plans_dict),"message": state['messages'][-1].content}) #"conditions":smt,
    
    # print(f" node_old_plan_exist old_plan_score{old_plan_score}")
    
    if plan is None or old_plan_score.result.lower() in ['no',"'no"]:
        goto = "conditions_and_plans"
    else:
        print('НАШËЛ ПЛАН')
        found_plan_row = CACHE_DF[CACHE_DF['plan_id'] == int(old_plan_score.result)]
        # print(found_plan_row)
        plan = found_plan_row.iloc[0]['plan_text']
        goto = "executor"

    return Command(
        # this is the state update
        update={"plan": plan, "user_mess":user_mess},#'vremya_dengi':vremya_dengi, 'df':all_plans
        # this is a replacement for an edge
        goto=goto,
    )

def conditions_and_plans(state):# -> Command[Literal["node_scenario_plan", "node_atom_plan"]]:
    # print('cond')
    conditions = df[['Название сценария','Условия входа']].to_dict(orient='records')
    # print(f"state['messages'][-1].content {state['messages'][-1].content}")
    score_scen = planner_scen_grader.invoke({"conditions": conditions, "messages": state['messages'][-1].content})

    # print(f" node_conditions_and_plans score_scen{score_scen}")
    
    if score_scen.content.lower() not in ['no',"'no'"]:
        print('ПЛАН ПО СЦЕНАРИЮ')
        opisanie_scen = df[df['Название сценария'] == score_scen.content]['Описание сценария'].values[0]
        plan_pr = plan_scenar(opisanie_scen, state['messages'][-1].content)

        # print(f" node_conditions_and_plans plan_pr{plan_pr}")

        # tokens_prompt_tokens+=plan_pr['raw'].response_metadata['token_usage']['prompt_tokens']
        # tokens_completion_tokens+=plan_pr['raw'].response_metadata['token_usage']['completion_tokens']
        plan = plan_pr.content#['parsed'].steps
        start_mess = state['messages'][-1].content
        add_generated_plan(plan,start_mes=start_mess)
    else:
        print('АТОМАРНЫЙ ПЛАН')
        plan = plan_dinamic(state['messages'][-1].content).content

        # print(f" node_conditions_and_plans plan{plan}")
        
        start_mess = state['messages'][-1].content
        add_generated_plan(plan,start_mes=start_mess)
    return {'plan':plan}#'vremya_dengi':vremya_dengi, 'df':all_plans

# 
def node_executor(state):
    # print('exec')
    plan = state['plan']
    messages = state['messages'][-1].content
    t1, item_number, item = get_next_unfinished_item(plan, CACHE_DF)
    print(item)

    # json и этот итем передаём экзекьютору

    chain = get_executor(item)
    response = chain.invoke(messages)#, 'mess':messages
    print(response)
    
    # print(f" node_executor response {response} + mock_exec_ans {mock_exec_ans}")
    return {"messages": [response], "item":item}

def node_MOCK_exec(state):
    plan = state['plan']
    t1, item_number, item = get_next_unfinished_item(plan, CACHE_DF)
    mock_exec_ans = execute_item(item, state['user_mess'])
    curr_id = get_curr_plan_id(CACHE_DF, plan)

    mock_status = get_status()

    # if mock_status == "status code 200":

    #     mark_item_completed(CACHE_DF, curr_id, item_number)
    #     print(mock_status)
    # else:
    #     print(mock_status)


    #в этой ноде получаем ответ от экзекутора и отправляем на болталку 

    print(f"ОТВЕТ ОТ МОК ЭКЗЕКЬЮТОРА:\n{mock_status}")
    mark_item_completed(CACHE_DF, curr_id, item_number)
    
    update_plan_status(CACHE_DF, cur_plan_id=curr_id)
    display_dataframe_pretty(CACHE_DF, "Проверяем датафрейм планов в кэше")
    return {'plan':plan, "response_mock":mock_exec_ans +"\n" + mock_status}

def node_bolt(state):
    print("chat")
    plan = state['plan']
    item = state['item']
    messages = state.get("messages")
    print(messages[-1])
    chat_responce = chat_agent.invoke({'plan':plan, "item":item, "execution_result":state['messages'][-1].content, 'messages':extract_relevant_messages(messages)})
    return {"messages": [chat_responce]}

def get_graph_planner():
    """Body of graph"""
    workflow = StateGraph(ComplexState)

    workflow.add_node("old_plans_existance", node_old_plan_exist)
    workflow.add_node("conditions_and_plans", conditions_and_plans)
    workflow.add_node("executor", node_executor)
    workflow.add_node("action", tool_node)
    workflow.add_node("MOCK_exec", node_MOCK_exec)
    workflow.add_node("chat", node_bolt)

    workflow.add_edge(START, "old_plans_existance")
    workflow.add_edge("conditions_and_plans", "executor")
    # We now add a conditional edge
    workflow.add_conditional_edges(
        "executor",
        should_continue,
        {
            "continue": "action",
            "end": "MOCK_exec",
        },
    )
    workflow.add_edge("action", "executor")
    workflow.add_edge("MOCK_exec", "chat")
    workflow.add_edge("chat",END)


    # Set up memory
    app = workflow.compile(checkpointer=memory)
    return app



# # Тест по сообщению
# from langchain_core.messages import HumanMessage

# CACHE_DF = pd.DataFrame(columns=['plan_id', 'plan_text','plan_status','completed_items','start_mes','summary'])

# user_input = input("Введите ваше сообщение: ")
# import uuid
# thread_id = str(uuid.uuid4())
# config = {"configurable": {"thread_id": thread_id}, "recursion_limit":10} # меняй тред айди для другого диалога. Можно раскомментить строчки сверху и заменить цифру треда на переменную выше

# _printed = set()
# while user_input.lower() != "=":
#     for event in app.stream({"messages": ("user", user_input)}, config, stream_mode="values"):
#         _print_event(event, _printed)

#     user_input = input("Введите следующее сообщение (или '=' для выхода): ")


# # print(app.get_state(config=config))# получить слепок стейта

# app.invoke({"messages": ("user", 'шашлыки любишь?')}, config=config)
