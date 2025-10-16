from langchain.tools import tool
from langchain.chat_models import init_chat_model

from langchain_core.messages import AnyMessage, SystemMessage, ToolMessage,HumanMessage

from typing_extensions import TypedDict, Annotated
import operator
from typing import Literal
from langgraph.graph import StateGraph, START, END


llm =init_chat_model(
    model="gemini-2.5-flash",
    api_key="AIzaSyAkLEmiJg9IXk-LAoKOojQkYDhxTG2py9U",
    temperature=0
)

class MessagesState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    llm_calls: int


@tool
def multiply(a:int,b:int)->int:
    """Multiply a and b.

    Args:
        a: first int
        b: second int
    """
    return a*b

@tool
def add(a: int, b: int) -> int:
    """Adds a and b.

    Args:
        a: first int
        b: second int
    """
    return a + b


@tool
def divide(a: int, b: int) -> float:
    """Divide a and b.

    Args:
        a: first int
        b: second int
    """
    return a / b

tools = [add, multiply, divide]
tools_by_name = {tool.name: tool for tool in tools}
llm_with_tools = llm.bind_tools(tools)


def llm_call(state: dict):
    """LLM decides whether to call a tool or not"""

    return {
        "messages": [
            llm_with_tools.invoke(
                [
                    SystemMessage(
                        content="You are a helpful assistant tasked with performing arithmetic on a set of inputs."
                    )
                ]
                + state["messages"]
            )
        ],
        "llm_calls": state.get('llm_calls', 0) + 1
    }

def tool_node(state:dict):
    """ performs tool call """
    results=[]

    for tool_call in state['messages'][-1].tool_calls:
        tool = tools_by_name[tool_call.name]
        tool_result = tool.invoke(tool_call.args)
        results.append(ToolMessage(content=tool_result, tool_call=tool_call))

    return {"messages": results}

def should_continue(state: MessagesState) -> Literal["tool_node", END]:
    """Decide if we should continue the loop or stop based upon whether the LLM made a tool call"""

    messages = state["messages"]
    last_message = messages[-1]
   
    if last_message.tool_calls:
        return "tool_node"

    return END



agent_builder = StateGraph(MessagesState)
agent_builder.add_node("llm_call", llm_call)
agent_builder.add_node("tool_node", tool_node)
agent_builder.add_edge(START, "llm_call")
agent_builder.add_conditional_edges(
    "llm_call",
    should_continue,
    ["tool_node", END]
)
agent_builder.add_edge("tool_node", "llm_call")
agent = agent_builder.compile()

from IPython.display import Image, display
display(Image(agent.get_graph(xray=True).draw_mermaid_png()))


messages = [HumanMessage(content="Add 3 and 4.")]
messages = agent.invoke({"messages": messages})
for m in messages["messages"]:
    m.pretty_print()