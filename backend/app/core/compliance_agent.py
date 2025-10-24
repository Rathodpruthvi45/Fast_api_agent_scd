from langchain.agents import AgentType, initialize_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import Tool
from langchain.memory import VectorStoreRetrieverMemory, ConversationBufferMemory, CombinedMemory
from langchain_chroma import Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain.schema import AIMessage, HumanMessage
from typing import List, Dict, Any
from ..models.compliance_models import ComplianceRule
from .compliance_checker import ComplianceChecker
import chromadb
import json
import os

class ComplianceAgent:
    def __init__(self, api_key: str):
        """Initialize the Compliance Agent with persistent memory"""

        # === Setup persistent Chroma vector database ===
        self.persist_directory = "./chroma_db"
        os.makedirs(self.persist_directory, exist_ok=True)

        self.client = chromadb.PersistentClient(path=self.persist_directory)
        self.embeddings = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")

        # Reuse the same collection for all API calls
        self.vector_store = Chroma(
            client=self.client,
            collection_name="gemini_memory_collection",
            embedding_function=self.embeddings
        )

        # === Create memory system ===
        # Use only ConversationBufferMemory for the agent (avoids key conflicts)
        self.conversation_memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            input_key="input",
            output_key="output"
        )

        # Keep vector store for semantic search (we'll use it manually)
        self.vector_memory = self.vector_store.as_retriever(search_kwargs={"k": 3})

        # === Initialize LLM ===
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            temperature=0,
            google_api_key=api_key,
            convert_system_message_to_human=True
        )

        # === Setup tools and agent ===
        self.tools = self._create_tools()
        self.agent = initialize_agent(
            tools=self.tools,
            llm=self.llm,
            memory=self.conversation_memory,  # Only use conversation memory for agent
            agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            return_intermediate_steps=False
        )

    # ---------------- TOOLS ---------------- #
    def _create_tools(self) -> List[Tool]:
        """Create tools for the agent to use"""
        return [
            Tool(
                name="check_compliance_rules",
                func=self._check_compliance_rules,
                description="Check compliance rules against the system. Input should be a list of compliance rules."
            ),
            Tool(
                name="analyze_compliance_results",
                func=self._analyze_compliance_results,
                description="Analyze compliance check results and provide insights. Input should be the results from compliance checks."
            )
        ]

    def _check_compliance_rules(self, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute compliance checks using the ComplianceChecker"""
        try:
            if isinstance(rules, str):
                rules = json.loads(rules)
            if not isinstance(rules, list):
                return [{"name": "invalid_input", "description": "Rules must be a list", "compliant": False}]
            return ComplianceChecker.check_all_rules(rules)
        except Exception as e:
            return [{"name": "error", "description": f"Error: {e}", "compliant": False}]

    def _analyze_compliance_results(self, results: List[Dict[str, Any]]) -> str:
        """Analyze compliance results and provide insights"""
        if isinstance(results, str):
            try:
                results = json.loads(results)
            except Exception:
                return results
        if isinstance(results, dict) and 'results' in results:
            results = results['results']
        if not isinstance(results, list):
            return "Unable to analyze results: expected a list of result dicts."

        compliant_count = sum(1 for r in results if isinstance(r, dict) and r.get('compliant', False))
        non_compliant_count = len(results) - compliant_count

        analysis = [
            f"Compliance Analysis Summary:",
            f"- Total rules checked: {len(results)}",
            f"- Compliant rules: {compliant_count}",
            f"- Non-compliant rules: {non_compliant_count}",
            "\nDetailed Findings:"
        ]

        for result in results:
            if not isinstance(result, dict):
                continue
            status = "Compliant" if result.get('compliant', False) else "Non-compliant"
            analysis.append(f"\n{result.get('name', 'Unnamed Rule')}:")
            analysis.append(f"- Status: {status}")
            analysis.append(f"- Current Value: {result.get('current_value', 'N/A')}")
            analysis.append(f"- Expected Value: {result.get('expected_value', 'N/A')}")

        return "\n".join(analysis)

    # ---------------- MAIN FUNCTIONS ---------------- #
    async def process_query(self, query: str, rules: List[ComplianceRule]) -> Dict[str, Any]:
        """
        API 1: Process PDF / compliance rules, analyze, and store in persistent memory.
        """
        try:
            formatted_rules = []
            for rule in rules:
                if isinstance(rule, dict):
                    formatted = rule
                else:
                    formatted = {
                        'name': getattr(rule, 'name', 'unnamed_rule'),
                        'description': getattr(rule, 'description', ''),
                        'check_type': getattr(rule, 'check_type', ''),
                        'registry_key': getattr(rule, 'registry_key', None),
                        'value_name': getattr(rule, 'value_name', None),
                        'expected_value': getattr(rule, 'expected_value', None),
                    }
                formatted_rules.append(formatted)

            compliance_results = self._check_compliance_rules(formatted_rules)
            analysis = self._analyze_compliance_results(compliance_results)

            # Save context in Chroma memory (for long-term semantic search)
            context_text = f"Query: {query}\nAnalysis:\n{analysis}"
            self.vector_store.add_texts([context_text])

            # Manually retrieve relevant past context from vector store
            relevant_docs = self.vector_memory.get_relevant_documents(query)
            relevant_context = "\n".join([doc.page_content for doc in relevant_docs[:2]])
            
            # Combine with current query
            enhanced_query = f"Relevant past context:\n{relevant_context}\n\nCurrent query: {query}\n\n{analysis}"

            # Use agent with enhanced query
            agent_response = await self.agent.arun(input=enhanced_query)

            # Save agent response to vector store for future semantic search
            self.vector_store.add_texts([f"Query: {query}\nAgent response: {agent_response}"])

            return {
                "results": compliance_results,
                "analysis": analysis,
                "agent_response": agent_response
            }

        except Exception as e:
            return {
                "error": f"Error processing query: {str(e)}",
                "results": [],
                "analysis": "",
                "agent_response": ""
            }

    async def ask_question(self, question: str) -> Dict[str, Any]:
        """
        API 2: Ask a question with full conversation memory
        """
        try:
            # Manually retrieve relevant past context from vector store
            relevant_docs = self.vector_memory.get_relevant_documents(question)
            relevant_context = "\n".join([doc.page_content for doc in relevant_docs[:2]])
            
            # Combine with current question
            if relevant_context.strip():
                enhanced_question = f"Relevant past information:\n{relevant_context}\n\nCurrent question: {question}"
            else:
                enhanced_question = question

            # Use the agent (which has conversation memory)
            agent_response = await self.agent.arun(input=enhanced_question)

            # Store in vector store for long-term semantic retrieval
            self.vector_store.add_texts([
                f"Question: {question}\nAnswer: {agent_response}"
            ])

            return {"agent_response": agent_response}

        except Exception as e:
            return {
                "error": f"Error processing question: {str(e)}", 
                "agent_response": ""
            }

    def clear_conversation_memory(self):
        """Clear only the short-term conversation memory (not vector store)"""
        self.conversation_memory.clear()

    def get_conversation_history(self) -> List[Dict[str, str]]:
        """Get the current conversation history"""
        messages = self.conversation_memory.chat_memory.messages
        history = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                history.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                history.append({"role": "assistant", "content": msg.content})
        return history