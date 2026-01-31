# Stub for Query Parser
# Determines if the user wants to search, summarize, or ask a general question

class QueryParser:
    def parse(self, query: str) -> dict:
        query = query.lower()
        if "summarize" in query:
            return {"intent": "summarize", "target": query.replace("summarize", "").strip()}
        elif "python file" in query or "file" in query:
             return {"intent": "search", "query": query}
        else:
             return {"intent": "ask", "query": query}
