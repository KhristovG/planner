import pandas as pd
import uuid

CACHE_DF = pd.DataFrame(columns=["plan_id", "plan_text", "plan_status", "completed_items", "start_mes", "summary"])
thread_id = str(uuid.uuid4())
config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 10}
_printed = set()

testing_dialog = [
        "Привет, как дела?",
        "Супер, меня зовут Максим",
        "Как меня зовут",
        "Расскажи про кошек ",
        "Теперь про собак" ,
]

for question in testing_dialog:
    events = app.stream(
        {"messages": ("user", question)}, config, stream_mode="values"
    )
    for event in events:
        _print_event(event, _printed)
import pandas as pd
import uuid

CACHE_DF = pd.DataFrame(columns=["plan_id", "plan_text", "plan_status", "completed_items", "start_mes", "summary"])
thread_id = str(uuid.uuid4())
config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 10}
_printed = set()

testing_dialog = [
        "Привет, как дела?",
        "Супер, меня зовут Максим",
        "Как меня зовут",
        "Расскажи про кошек ",
        "Теперь про собак" ,
]

for question in testing_dialog:
    events = app.stream(
        {"messages": ("user", question)}, config, stream_mode="values"
    )
    for event in events:
        _print_event(event, _printed)
import pandas as pd
import uuid

CACHE_DF = pd.DataFrame(columns=["plan_id", "plan_text", "plan_status", "completed_items", "start_mes", "summary"])
thread_id = str(uuid.uuid4())
config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 10}
_printed = set()

testing_dialog = [
        "Привет, как дела?",
        "Супер, меня зовут Максим",
        "Как меня зовут",
        "Расскажи про кошек ",
        "Теперь про собак" ,
]

for question in testing_dialog:
    events = app.stream(
        {"messages": ("user", question)}, config, stream_mode="values"
    )
    for event in events:
        _print_event(event, _printed)
