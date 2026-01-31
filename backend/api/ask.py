from fastapi import APIRouter
from pydantic import BaseModel
from backend.services.query_parser import QueryParser
from backend.services.summarizer import Summarizer

router = APIRouter()
parser = QueryParser()
summarizer = Summarizer()

class AskRequest(BaseModel):
    question: str

class AskResponse(BaseModel):
    answer: str
    sources: list[str]

@router.post("/ask", response_model=AskResponse)
async def ask_question(req: AskRequest):
    intent = parser.parse(req.question)
    
    # Simple logic for now
    if intent['intent'] == 'summarize':
        # In a real app we'd fetch the file content first
        summary = summarizer.summarize(intent['target'])
        return {"answer": summary, "sources": [intent['target']]}
    
    return {"answer": f"I understood you want to {intent['intent']}: {req.question}", "sources": []}
