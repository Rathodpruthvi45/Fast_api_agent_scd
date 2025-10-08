
from fastapi import FastAPI, File, UploadFile
from io import BytesIO
from fastapi import APIRouter
from ...core.compliance_checker import ComplianceChecker

router=APIRouter(prefix="/complince", tags=["SID Complince"])

@router.get("/sid")
def single_sid():
    print("Hi i am the best")
    result=ComplianceChecker.get_current_user_sid()
    return {"sid": result}
