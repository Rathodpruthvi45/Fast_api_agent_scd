import os
import datetime
from typing import Annotated
from typing_extensions import TypedDict
import uuid
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, BaseMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_tavily import TavilySearch
from langgraph.graph.message import add_messages

# Set your Tavily API key here
os.environ["TAVILY_API_KEY"] = "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"

# Define the custom "get current time" tool
@tool
def get_current_time() -> str:
    """Returns the current time in HH:MM AM/PM format."""
    now = datetime.datetime.now()
    return now.strftime("%I:%M %p")

class ReflexionAgent:
    def __init__(self):
        self.tools = [TavilySearch(max_results=5), get_current_time]
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            api_key="AIzaSyAkLEmiJg9IXk-LAoKOojQkYDhxTG2py9U"
        ).bind_tools(self.tools)
        # Initialize the checkpointer for memory
        self.checkpointer = InMemorySaver()

    class State(TypedDict):
        messages: Annotated[list[BaseMessage], add_messages]

    def chatbot(self, state: State):
        response = self.llm.invoke(state["messages"])
        return {"messages": [response]}

    def tool_node(self, state: State):
        tool_node = ToolNode(self.tools)
        return tool_node.invoke(state)

    def should_continue(self, state: State):
        last_message = state['messages'][-1]
        if last_message.tool_calls:
            return "tools"
        return "end"

    def graph(self):
        graph_builder = StateGraph(self.State)
        graph_builder.add_node("chatbot", self.chatbot)
        graph_builder.add_node("tools", self.tool_node)
        graph_builder.add_edge(START, "chatbot")
        graph_builder.add_conditional_edges(
            "chatbot",
            self.should_continue,
            {"tools": "tools", "end": END}
        )
        graph_builder.add_edge("tools", "chatbot")
        # Compile the graph with the checkpointer for memory
        return graph_builder.compile(checkpointer=self.checkpointer)

    def stream_graph_updates(self, user_input: str):
        graph = self.graph()
        # Generate a unique thread ID for each session
        thread_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}

        for event in graph.stream(
            {"messages": [HumanMessage(content=user_input)]},
            config=config 
        ):
            for key, value in event.items():
                if key == "chatbot":
                    content = value["messages"][-1].content
                    if content:
                        print("Assistant:", content)
                elif key == "tools":
                    print(f"Tool Output: {value}")

if __name__ == "__main__":
    agent = ReflexionAgent()
    while True:
        try:
            user_input = input("User: ")
            if user_input.lower() in ["quit", "exit", "q"]:
                print("Goodbye!")
                break
            # Generate a consistent thread_id for multi-turn conversations
            thread_id = str(uuid.uuid4())
            config = {"configurable": {"thread_id": thread_id}}

            
            agent.stream_graph_updates(user_input)
        except Exception as e:
            print(f"An error occurred: {e}")
            break
