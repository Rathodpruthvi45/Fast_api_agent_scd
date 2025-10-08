# FastAPI endpoints for rules
from typing import List
from ...models.compliance_models import (
    ComplianceRule,
    ComplianceRuleForLLM,
    ComplianceRuleList,
)
import re
from langchain_core.output_parsers import PydanticOutputParser
from langchain.prompts import PromptTemplate
from langchain.chat_models import init_chat_model
from langchain.schema import HumanMessage


class RuleExtractor:

    def __init__(self):
        self.parser = PydanticOutputParser(pydantic_object=ComplianceRuleList)
        self.llm = init_chat_model(
            "gemini-2.5-flash",
            model_provider="google_genai",
            api_key="AIzaSyAkLEmiJg9IXk-LAoKOojQkYDhxTG2py9U",
        )

    def rule_extractor(self, text: str) -> List[ComplianceRule]:
        """Extract compliance rules from text"""
        if not text or text.strip() == "":
            return []
        cleaned_text = self.clean_text_for_llm(text)
        max_chars = 10000
        if len(cleaned_text) > max_chars:
            cleaned_text = cleaned_text[:max_chars] + "..."
        prompt = f"""
                You are a Windows compliance rule extractor.

                Scan the document text for any **registry paths** (HKLM, HKCU, HKU, HKEY_LOCAL_MACHINE, etc.)
                and extract the **registry key + value names + expected values**.

                If no registry is found, return an empty list [].

                Text:
                {cleaned_text}

                Return JSON matching this schema:
                {self.parser.get_format_instructions()}
                """
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            rule = self.parser.parse(response.content)
            result= self.rule_extractor_from_llm_format(rule.model_dump())
            return result

        except Exception as e:
            print(f"LLM prediction error: {e}")
            return []

    def clean_text_for_llm(self, text: str) -> str:
        """Clean text for LLM processing"""
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", " ", text)
        text = re.sub(r"\s+", " ", text)
        text = text.replace("\\\\", "\\")

        return text.strip()

    def rule_extractor_from_llm_format(self,response):
        full_text=[]
        print("this is the text rule extractor ")
        for rule in response:
            print(rule)
            for check in rule["registry_checks"]:
                full_text.append(
                    {
                        'name': rule['name'],
                        'description': rule['description'],
                        'check_type':rule['check_type'],
                        'registry_key': rule['registry_key'],
                        'value_name':check['value_name'],
                        'expected_value':check['expected_value']
                    }
                )
        return full_text
rules_extractor = RuleExtractor()
