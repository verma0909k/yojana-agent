"""FastAPI endpoints exposing YojanaAgent LangGraph loop."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from yojanaagent.brain.graph import build_graph
from yojanaagent.shared.schemas import AgentState, CitizenProfile

app = FastAPI(title="YojanaAgent API", version="1.0.0")
graph = build_graph()


class MatchRequest(BaseModel):
    profile: CitizenProfile
    user_query: str = ""
    language: str = "en"


@app.get("/")
def health_check():
    return {"status": "ok", "agent": "YojanaAgent"}


@app.post("/match")
def match_schemes(request: MatchRequest):
    try:
        initial_state = AgentState(
            profile=request.profile,
            user_query=request.user_query,
            language=request.language
        )
        final_state = graph.invoke(initial_state)
        return {
            "status": "success",
            "eligible_schemes": [
                m.model_dump() for m in final_state["match_results"] if m.status == "ELIGIBLE"
            ],
            "almost_schemes": [
                m.model_dump() for m in final_state["match_results"] if m.status == "ALMOST"
            ],
            "trace_steps": [t.model_dump() for t in final_state["trace_steps"]],
            "final_response": final_state["final_response"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
