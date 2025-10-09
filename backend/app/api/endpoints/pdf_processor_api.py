from fastapi import FastAPI, File, UploadFile
from io import BytesIO
from fastapi import APIRouter
from ...services.pdf_exctractor import pdfloader
from ...api.endpoints.rules import rules_extractor
from ...core.compliance_checker import ComplianceChecker
router = APIRouter(prefix="/upload", tags=["Documents"])


@router.post("/upload_pdf")
async def pdf_upload(file: UploadFile = File(...)):
    contents = await file.read()
    file_like = BytesIO(contents)
    text = pdfloader.extract_text_from_pdf(file_like)
    rule_extractor = rules_extractor.rule_extractor(text)
    response=ComplianceChecker.check_all_rules(rule_extractor)
    return {"rules":response}
