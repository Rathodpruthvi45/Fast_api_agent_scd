from langchain.agents import AgentType, initialize_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import Tool
from typing import List, Dict
from ..models.compliance_models import ComplianceRule, ComplianceRuleList
from .compliance_checker import ComplianceChecker

class ComplianceAgent:
    def __init__(self, api_key: str):
        """Initialize the compliance agent with Google API key"""
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-pro",
            temperature=0,
            google_api_key=api_key,
            convert_system_message_to_human=True
        )
        self.tools = self._create_tools()
        self.agent = initialize_agent(
            self.tools,
            self.llm,
            agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True
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

    def _check_compliance_rules(self, rules: List[Dict]) -> List[Dict]:
        """Execute compliance checks using the ComplianceChecker"""
        return ComplianceChecker.check_all_rules(rules)

    def _analyze_compliance_results(self, results: List[Dict]) -> str:
        """Analyze compliance results and provide insights"""
        compliant_count = sum(1 for r in results if r.get('compliant', False))
        non_compliant_count = len(results) - compliant_count
        
        analysis = [
            f"Compliance Analysis Summary:",
            f"- Total rules checked: {len(results)}",
            f"- Compliant rules: {compliant_count}",
            f"- Non-compliant rules: {non_compliant_count}",
            "\nDetailed Findings:"
        ]
        
        for result in results:
            status = " Compliant" if result.get('compliant', False) else "Non-compliant"
            analysis.append(f"\n{result['name']}:")
            analysis.append(f"- Status: {status}")
            analysis.append(f"- Current Value: {result.get('current_value', 'N/A')}")
            analysis.append(f"- Expected Value: {result.get('expected_value', 'N/A')}")
            
        return "\n".join(analysis)

    async def process_query(self, query: str, rules: List[ComplianceRule]) -> Dict:
        """Process a natural language query about compliance"""
        try:
            # Convert rules to the format expected by ComplianceChecker
            formatted_rules = [{
                'name': rule.name,
                'description': rule.description,
                'check_type': rule.check_type,
                'registry_key': rule.registry_key,
                'value_name': rule.expected_value,  # Adjust based on your actual structure
                'expected_value': rule.expected_value
            } for rule in rules]

            # First check compliance
            compliance_results = self._check_compliance_rules(formatted_rules)
            
            # Then analyze the results
            analysis = self._analyze_compliance_results(compliance_results)
            
            # Let the agent provide insights based on the query and results
            agent_response = await self.agent.arun(
                f"{query}\n\nBased on the compliance results:\n{analysis}"
            )
            
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