from fastapi import FastAPI, File, UploadFile, HTTPException
from io import BytesIO
from fastapi import APIRouter
from typing import Optional
from pydantic import BaseModel
from ...services.pdf_exctractor import pdfloader
from ...api.endpoints.rules import rules_extractor
from ...core.compliance_checker import ComplianceChecker
from ...core.compliance_agent import ComplianceAgent
import os

# Initialize AI agent
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "AIzaSyAkLEmiJg9IXk-LAoKOojQkYDhxTG2py9U")
compliance_agent = ComplianceAgent(api_key=GOOGLE_API_KEY)
router = APIRouter(prefix="/upload", tags=["Documents"])


class PDFAnalysisRequest(BaseModel):
    query: Optional[str] = "Analyze the compliance status and provide detailed insights."

@router.post("/upload_pdf")
async def pdf_upload(file: UploadFile = File(...), analysis_request: PDFAnalysisRequest = None):
    try:
        # Read and process PDF
        contents = await file.read()
        file_like = BytesIO(contents)
        text = pdfloader.extract_text_from_pdf(file_like)
        
        # Extract rules from PDF
        extracted_rules = rules_extractor.rule_extractor(text)
        
        if not extracted_rules:
            raise HTTPException(
                status_code=400,
                detail="No compliance rules could be extracted from the PDF"
            )
            
        # Use AI agent to analyze rules
        query = analysis_request.query if analysis_request else "Analyze the compliance status and provide detailed insights."
        agent_response = await compliance_agent.process_query(query, extracted_rules)
        
        return {
            "success": True,
            "file_name": file.filename,
            "extracted_rules_count": len(extracted_rules),
            "compliance_analysis": agent_response
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing PDF: {str(e)}"
        )
