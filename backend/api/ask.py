from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, constr
import asyncio

# Import au niveau module pour détecter les problèmes au démarrage
try:
    from backend.app.llm.client import ask_llm
except Exception as import_err:
    # En cas de problème d'import, on lève une exception au démarrage
    raise RuntimeError(f"Echec d'import de l'LLM client: {import_err}") from import_err

router = APIRouter()

# Configuration basique (peut être déplacée vers config/env)
DEFAULT_MAX_TOKENS = 1024
LLM_TIMEOUT_SECONDS = 20  # Ajuster selon performances de l'LLM


class AskRequest(BaseModel):
    # Validation stricte: au moins 1 caractère, max 2000 (ajuster si besoin)
    question: constr(min_length=1, max_length=2000)


class AskResponse(BaseModel):
    answer: str
    sources: list[str]  # Gardé pour compat., rester vide tant que non implémenté


@router.post(
    "/ask",
    response_model=AskResponse,
    summary="Poser une question à l'LLM",
    description="Envoie une question à l'LLM et renvoie la réponse générée. "
                "La requête est soumise à une validation (longueur min/max) et un timeout.",
)
async def ask_question(req: AskRequest) -> AskResponse:
    question = req.question.strip()
    if not question:
        # Par sécurité, même après strip
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La question ne peut pas être vide."
        )

    try:
        # Timeout pour éviter les blocages
        answer = await asyncio.wait_for(
            ask_llm(question, max_tokens=DEFAULT_MAX_TOKENS),
            timeout=LLM_TIMEOUT_SECONDS
        )
        # Normalisation minimale de la réponse
        answer = (answer or "").strip()
        if not answer:
            answer = "Aucune réponse générée par le modèle."

        return AskResponse(answer=answer, sources=[])

    except asyncio.TimeoutError:
        # Timeout de l'LLM -> 504
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Timeout de l'LLM après {LLM_TIMEOUT_SECONDS} secondes."
        )
    except Exception as e:
        # Erreur backend LLM -> 502
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erreur du backend LLM: {str(e)}"
        )