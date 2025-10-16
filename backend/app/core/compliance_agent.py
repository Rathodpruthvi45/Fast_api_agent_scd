from langchain.agents import AgentType, initialize_agent
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain.tools import Tool
from langchain.memory import VectorStoreRetrieverMemory
from langchain_chroma import Chroma
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any
from ..models.compliance_models import ComplianceRule
from .compliance_checker import ComplianceChecker
import os
import json

# Chroma Settings for Windows (avoids Rust DLL issues)
chroma_settings = Settings(
    chroma_db_impl="duckdb+parquet",  
    persist_directory=".chromadb"
)

class ComplianceAgent:
    def __init__(self, api_key: str):
        """Initialize the compliance agent with Google API key"""
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0,
            google_api_key=api_key,
            convert_system_message_to_human=True
        )
        self.tools = self._create_tools()
        
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=api_key
        )
        
        self.persist_directory = ".chromadb"
        os.makedirs(self.persist_directory, exist_ok=True)
        
        # Initialize Chroma vectorstore with settings
        self.vectorstore = Chroma(
            persist_directory=self.persist_directory,
            embedding_function=self.embeddings,
            collection_name="compliance_agent_memory",
            client_settings=chroma_settings
        )
        
        # Memory using the vectorstore
        self.memory = VectorStoreRetrieverMemory(
            retriever=self.vectorstore.as_retriever(search_kwargs={"k": 5})
        )
        
        # Initialize LangChain agent
        self.agent = initialize_agent(
            self.tools,
            self.llm,
            agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            memory=self.memory
        )

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
                try:
                    rules = json.loads(rules)
                except Exception:
                    return [{
                        'name': 'invalid_input',
                        'description': 'Expected JSON list of rules or list of dicts',
                        'check_type': '',
                        'registry_key': None,
                        'value_name': None,
                        'expected_value': None,
                        'compliant': False,
                        'current_value': 'invalid input'
                    }]
            if not isinstance(rules, list):
                return [{
                    'name': 'invalid_input',
                    'description': 'Rules must be a list of rule dicts',
                    'check_type': '',
                    'registry_key': None,
                    'value_name': None,
                    'expected_value': None,
                    'compliant': False,
                    'current_value': 'invalid input'
                }]
            return ComplianceChecker.check_all_rules(rules)
        except Exception as e:
            return [{
                'name': 'error',
                'description': f'Error running compliance checks: {e}',
                'check_type': '',
                'registry_key': None,
                'value_name': None,
                'expected_value': None,
                'compliant': False,
                'current_value': None,
            }]

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
            return "Unable to analyze results: expected a list of result dicts or an analysis string."
        
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

    async def process_query(self, query: str, rules: List[ComplianceRule]) -> Dict[str, Any]:
        """Process a natural language query about compliance"""
        try:
            # Normalize rules to dict
            formatted_rules = []
            for rule in rules:
                if isinstance(rule, dict):
                    formatted = {
                        'name': rule.get('name', 'unnamed_rule'),
                        'description': rule.get('description', ''),
                        'check_type': rule.get('check_type', ''),
                        'registry_key': rule.get('registry_key', None),
                        'value_name': rule.get('value_name', None),
                        'expected_value': rule.get('expected_value', None),
                    }
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

            # Compliance check
            compliance_results = self._check_compliance_rules(formatted_rules)
            analysis = self._analyze_compliance_results(compliance_results)

            # Add to vectorstore memory and persist
            self.vectorstore.add_texts([f"{query}\n\nBased on the compliance results:\n{analysis}"])
            self.vectorstore.persist()

            agent_response = await self.agent.arun(f"{query}\n\nBased on the compliance results:\n{analysis}")
            self.vectorstore.add_texts([f"Agent response:\n{agent_response}"])
            self.vectorstore.persist()

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
        """Ask a follow-up question. Uses memory for context."""
        try:
            agent_response = await self.agent.arun(question)
            return {"agent_response": agent_response}
        except Exception as e:
            return {"error": f"Error processing question: {str(e)}", "agent_response": ""}
