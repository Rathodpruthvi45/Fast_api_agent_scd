import pdfplumber
import logging

logger = logging.getLogger(__name__)


class PDFLoader:
    def __init__(self):
        pass

    def extract_text_from_pdf(self, pdf_file) -> str:
        try:
            full_text = []
            with pdfplumber.open(pdf_file) as pdf:
                for page_number, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if text and text.strip():
                        full_text.append(f"---{page_number}---\n{text}")
                if not full_text:
                    logger.warning("PDF File is empty")
                    return "PDF File is empty"

                extracted_text = "\n\n".join(full_text)
                return extracted_text

        except Exception as e:
            logger.error(f"unable to upload a pdf file error:{e}")
            return ""


pdfloader = PDFLoader()
