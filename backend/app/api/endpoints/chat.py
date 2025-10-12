from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from ...core.Reflexion_agent import ReflexionAgent
from ...core.compliance_checker import complince_check
from ...services.pdf_exctractor import extract_text_from_pdf

router = APIRouter()
reflexion_agent = ReflexionAgent()


class ChatMessage(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    response: str
    conversation_history: List[Dict[str, Any]]


@router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(message: ChatMessage):
    """
    Chat endpoint that processes user messages and returns agent responses
    """
    try:
        # Process the message using the Reflexion agent
        response = reflexion_agent.process_user_query(message.message, message.context)

        # Get the conversation history
        conversation_history = reflexion_agent.get_conversation_history()

        return ChatResponse(
            response=response, conversation_history=conversation_history
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload-and-chat")
async def upload_and_chat(file: bytes, message: str):
    """
    Endpoint to handle PDF upload and initiate chat about its contents
    """
    try:
        # Extract text from PDF
        pdf_text = extract_text_from_pdf(file)

        # Initialize context with PDF content
        context = {"pdf_content": pdf_text, "document_type": "compliance_pdf"}

        # Process the message with the PDF context
        response = reflexion_agent.process_user_query(message, context)

        # Get conversation history
        conversation_history = reflexion_agent.get_conversation_history()

        return ChatResponse(
            response=response, conversation_history=conversation_history
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
