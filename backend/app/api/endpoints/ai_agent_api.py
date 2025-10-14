from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from ...models.compliance_models import ComplianceRule, ComplianceRuleList
from ...core.compliance_agent import ComplianceAgent
from pydantic import BaseModel
import os

router = APIRouter(prefix="/ai", tags=["AI Compliance Agent"])

# Get Google API key from environment variable
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "AIzaSyAkLEmiJg9IXk-LAoKOojQkYDhxTG2py9U")

# Initialize the agent
agent = ComplianceAgent(api_key=GOOGLE_API_KEY)

class ComplianceQuery(BaseModel):
    """Model for compliance queries"""
    query: str
    rules: List[ComplianceRule]

class ComplianceResponse(BaseModel):
    """Model for compliance agent responses"""
    results: List[dict]
    analysis: str
    agent_response: str

@router.post("/query", response_model=ComplianceResponse)
async def process_compliance_query(query: ComplianceQuery):
    """Process a natural language query about compliance"""
    try:
        response = await agent.process_query(query.query, query.rules)
        return ComplianceResponse(**response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze")
async def analyze_compliance(rules: ComplianceRuleList):
    """Analyze compliance rules without a specific query"""
    try:
        # Use empty query to just get compliance analysis
        response = await agent.process_query("Analyze the compliance status.", rules.rules)
        return ComplianceResponse(**response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))