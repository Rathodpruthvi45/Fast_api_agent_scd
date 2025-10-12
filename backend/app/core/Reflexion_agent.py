from typing import List, Dict, Any, Optional, Annotated
import json
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain.prompts import PromptTemplate
from langchain.chat_models import init_chat_model
from langchain.schema import HumanMessage
from typing_extensions import TypedDict


class ReflexionAgent:
    def __init__(self):
        self.llm = init_chat_model(
            "gemini-2.5-flash",
            model_provider="google_genai",
            api_key="AIzaSyAkLEmiJg9IXk-LAoKOojQkYDhxTG2py9U",
        )

    class State(TypedDict):
        messages: Annotated[list, add_messages]

    def chatbot(self, state: State):
        return {"messages": [self.llm.invoke(state["messages"])]}

    def graph(self):
        graph_builder = StateGraph(self.State)
        graph_builder.add_state(START, self.chatbot)
        graph_builder.add_edge("chatbot", END)
        graph = graph_builder.compile()
        return graph

    def stream_graph_updates(self, user_input: str):
        graph = self.graph()
        for event in graph.stream(
            {"messages": [{"role": "user", "content": user_input}]}
        ):
            for value in event.values():
                print("Assistant:", value["messages"][-1].content)
