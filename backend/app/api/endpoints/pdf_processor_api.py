from fastapi import FastAPI, File, UploadFile
from io import BytesIO
from fastapi import APIRouter
from ...services.pdf_exctractor import pdfloader
from ...api.endpoints.rules import rules_extractor

router = APIRouter(prefix="/upload", tags=["Documents"])


@router.post("/upload_pdf")
async def pdf_upload(file: UploadFile = File(...)):
    contents = await file.read()
    file_like = BytesIO(contents)
    text = pdfloader.extract_text_from_pdf(file_like)
    rule_extractor = rules_extractor.rule_extractor(text)
    return {"rules": rule_extractor}
