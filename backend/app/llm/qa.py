from backend.app.search.engine import search_index, get_document_content_by_id
from backend.app.llm.client import ask_llm
import asyncio # Import asyncio for async operations

async def answer_question(question: str, k: int = 3) -> str:
    """
    Answers a question by retrieving relevant documents, forming context,
    and querying the local LLM.
    """
    print(f"[QA] Searching for context for question: '{question}'")
    # Search returns unique_chunk_ids, not full content directly
    relevant_chunk_ids = search_index(question, k=k)

    if not relevant_chunk_ids or len(relevant_chunk_ids) == 1 and "⚠️" in relevant_chunk_ids[0]:
        print("[QA] No relevant documents found or index is empty.")
        # If no context, ask LLM a general question or inform user
        if "⚠️" in relevant_chunk_ids[0]: # Specific message from engine.py
            return relevant_chunk_ids[0]
        return await ask_llm(f"Based on your general knowledge, {question}")


    context_parts = []
    # Retrieve the actual content for each relevant chunk ID
    print(f"[QA] Found {len(relevant_chunk_ids)} relevant chunks. Retrieving content...")
    for chunk_id in relevant_chunk_ids:
        chunk_content = get_document_content_by_id(chunk_id)
        if chunk_content:
            context_parts.append(f"--- Document Chunk ID: {chunk_id} ---\n{chunk_content}")
    
    context = "\n\n".join(context_parts)
    print(f"[QA] Context assembled (first 200 chars): {context[:200]}...")

    if not context.strip():
        print("[QA] No content retrieved from relevant chunks. Asking general question.")
        return await ask_llm(f"Based on your general knowledge, {question}")

    prompt = f"""
You are LocalMind, an intelligent AI assistant that answers questions based on information available on the user's local computer.
You *must* use ONLY the provided context to answer the question. If the answer cannot be found in the context, state that clearly and politely.
Do not make up information. Keep your answers concise and directly to the point.

Context from Local Files:
{context}

---

Question:
{question}

---

Answer:
"""
    print(f"[QA] Sending prompt to LLM...")
    llm_answer = await ask_llm(prompt)
    print(f"[QA] Received LLM answer.")
    return llm_answer