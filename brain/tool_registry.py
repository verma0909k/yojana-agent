"""Dynamic Tool Registry with typed Pydantic input/output validation and execution logging."""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional
from pydantic import BaseModel, ConfigDict, Field

from experience.actions.notifier import NotificationService
from experience.actions.pdf_filler import generate_application_pdf
from experience.dashboard.application_tracker import ApplicationTracker
from experience.intake.hinglish import NaturalLanguageIntake
from experience.intake.vault import DocumentVault
from knowledge.monitor import MemoryStore
from knowledge.rule_engine import evaluate_all, evaluate_scheme
from knowledge.schemes.data import load_all_schemes
from knowledge.semantic_search import SemanticSearchEngine
from knowledge.verifier import Verifier
from shared.schemas import (
    CitizenProfile,
    DraftGenerationRequest,
    EligibilityStatus,
    Fact,
    MatchResult,
    Scheme,
    ToolExecutionResult,
)


def _dict_to_profile(profile_data: Optional[dict[str, Any]]) -> CitizenProfile:
    """Safely converts raw dictionaries or serialized profile representations into a CitizenProfile."""
    if not profile_data:
        return CitizenProfile()
    profile = CitizenProfile()
    for k, v in profile_data.items():
        if hasattr(profile, k):
            if isinstance(v, dict) and "value" in v:
                setattr(profile, k, Fact(value=v["value"], confidence=v.get("confidence", 1.0)))
            elif isinstance(v, Fact):
                setattr(profile, k, v)
            else:
                setattr(profile, k, Fact(value=v, confidence=1.0))
    return profile


# --- Tool Input Schemas ---

class ToolBaseInput(BaseModel):
    model_config = ConfigDict(extra="ignore")


class ExtractProfileInput(ToolBaseInput):
    text: str = Field(description="Natural language statement from citizen in Hindi, English, or Hinglish")
    existing_profile: Optional[dict[str, Any]] = Field(default=None, description="Existing citizen profile dictionary")


class SearchSchemesInput(ToolBaseInput):
    query: str = Field(description="Citizen query or intent description")
    top_k: int = Field(default=5, description="Number of candidate schemes to retrieve")
    where_filter: Optional[dict[str, Any]] = Field(default=None, description="Optional metadata filter (e.g. ministry)")


class GetSchemeDetailsInput(ToolBaseInput):
    scheme_id: str = Field(description="Unique scheme identifier (e.g. pm-kisan, aicte-pragati-scholarship)")


class RetrieveEvidenceInput(ToolBaseInput):
    scheme_id: str = Field(description="Scheme ID to retrieve official document text and source metadata for")


class IdentifyGapsInput(ToolBaseInput):
    scheme_ids: list[str] = Field(description="List of scheme IDs to check for missing facts")
    profile_data: Optional[dict[str, Any]] = Field(default=None, description="Current citizen profile data")


class AskCitizenInput(ToolBaseInput):
    field_name: str = Field(description="Field name to formulate question for (e.g. is_bpl, land_holding_acres)")
    language: str = Field(default="en", description="Language code: 'en' or 'hi'")


class VerifyOfficialSourceInput(ToolBaseInput):
    url: str = Field(description="Official government portal URL to verify reachability and HTTP integrity")


class CompareEligibilityInput(ToolBaseInput):
    profile_data: Optional[dict[str, Any]] = Field(default=None, description="Citizen profile facts")
    scheme_ids: Optional[list[str]] = Field(default=None, description="Optional list of specific scheme IDs to evaluate")


class CheckDocumentsInput(ToolBaseInput):
    scheme_id: str = Field(description="Target scheme identifier")
    available_documents: list[str] = Field(default_factory=list, description="Documents citizen currently possesses")


class ApplicationChecklistInput(ToolBaseInput):
    scheme_id: str = Field(description="Target scheme identifier")


class GenerateApplicationDocInput(ToolBaseInput):
    scheme_id: str = Field(description="Target scheme identifier")
    profile_data: Optional[dict[str, Any]] = Field(default=None, description="Citizen profile data")


class CreateApplicationTaskInput(ToolBaseInput):
    scheme_id: str = Field(description="Scheme identifier")
    citizen_id: str = Field(default="active_citizen", description="Citizen identifier")
    notes: str = Field(default="", description="Initial application notes")


class UpdateApplicationStatusInput(ToolBaseInput):
    task_id: str = Field(description="Task identifier")
    status: str = Field(description="New status (e.g. DRAFT, READY_FOR_SUBMISSION, SUBMITTED)")
    notes: str = Field(default="", description="Update notes")


class SaveMemoryInput(ToolBaseInput):
    key: str = Field(description="Storage key")
    value: Any = Field(description="Value or profile to persist")


class RetrieveMemoryInput(ToolBaseInput):
    key: str = Field(description="Storage key to retrieve")


class GetVaultDocumentsInput(ToolBaseInput):
    user_id: str = Field(default="active_citizen", description="Citizen identifier whose vault documents to inspect")


class DraftNotificationInput(ToolBaseInput):
    user_id: str = Field(default="active_citizen", description="Citizen identifier")
    event_type: str = Field(description="Event type e.g. DOCUMENT_EXPIRY, DEADLINE_REMINDER, SCHEME_UPDATE")
    recipient: str = Field(description="Email address, Telegram handle, or mobile number")
    channel: str = Field(default="email", description="Delivery channel ('email', 'telegram', 'sms')")
    language: str = Field(default="en", description="Target language ('en' or 'hi')")
    context_data: Optional[dict[str, Any]] = Field(default_factory=dict, description="Context parameters for the message")


class ExplainRejectionInput(ToolBaseInput):
    scheme_id: str = Field(description="Scheme ID to explain rejection for")
    profile_data: Optional[dict[str, Any]] = Field(default=None, description="Citizen profile facts")
    language: str = Field(default="en", description="Language code: 'en' or 'hi'")


class RecommendNextBestInput(ToolBaseInput):
    ineligible_scheme_id: str = Field(description="Scheme for which applicant did not qualify")
    profile_data: Optional[dict[str, Any]] = Field(default=None, description="Citizen profile facts")
    top_k: int = Field(default=3, description="Number of alternative schemes to recommend")



# --- Tool Definition Wrapper ---

@dataclass
class ToolDefinition:
    name: str
    description: str
    input_schema: type[BaseModel]
    func: Callable[..., Any]


class ToolRegistry:
    """Registry managing available tools, argument validation, and audited execution."""

    def __init__(self):
        self.tools: dict[str, ToolDefinition] = {}
        self.execution_log: list[dict[str, Any]] = []
        self._register_default_tools()

    def register(self, name: str, description: str, input_schema: type[BaseModel], func: Callable[..., Any]):
        self.tools[name] = ToolDefinition(
            name=name,
            description=description,
            input_schema=input_schema,
            func=func
        )

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        return self.tools.get(name)

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "schema": t.input_schema.model_json_schema()
            }
            for t in self.tools.values()
        ]

    def execute_tool(self, name: str, arguments: dict[str, Any]) -> ToolExecutionResult:
        """Validates arguments against Pydantic schema, runs tool, and records execution audit log."""
        tool = self.get_tool(name)
        timestamp = datetime.now(timezone.utc).isoformat()

        if not tool:
            err = f"Tool '{name}' is not registered in ToolRegistry. Available: {list(self.tools.keys())}"
            self.execution_log.append({"timestamp": timestamp, "tool": name, "success": False, "error": err})
            return ToolExecutionResult(tool_name=name, success=False, error=err)

        try:
            # Validate input against schema
            validated = tool.input_schema.model_validate(arguments or {})
            result_data = tool.func(**validated.model_dump())
            
            self.execution_log.append({
                "timestamp": timestamp,
                "tool": name,
                "arguments": arguments,
                "success": True,
            })
            return ToolExecutionResult(
                tool_name=name,
                success=True,
                data=result_data,
                metadata={"timestamp": timestamp}
            )
        except Exception as e:
            err_msg = f"Execution error in tool '{name}': {str(e)}"
            self.execution_log.append({
                "timestamp": timestamp,
                "tool": name,
                "arguments": arguments,
                "success": False,
                "error": err_msg
            })
            return ToolExecutionResult(
                tool_name=name,
                success=False,
                error=err_msg,
                metadata={"timestamp": timestamp}
            )

    # --- Tool Implementations ---

    def _register_default_tools(self):
        intake = NaturalLanguageIntake()
        search_engine = SemanticSearchEngine()
        verifier = Verifier()
        memory_store = MemoryStore()
        app_tracker = ApplicationTracker()

        # 1. extract_citizen_profile
        def run_extract_profile(text: str, existing_profile: Optional[dict[str, Any]] = None):
            base_profile = _dict_to_profile(existing_profile)
            updated = intake.parse_user_input(text, existing_profile=base_profile)
            return {
                "profile": updated.model_dump(),
                "known_fields": updated.known_fields(),
                "extracted_fields": [k for k, v in updated if getattr(v, "known", False)]
            }
        self.register("extract_citizen_profile", "Extracts structured citizen facts from conversational text in Hindi, Hinglish, or English.", ExtractProfileInput, run_extract_profile)

        # 2. search_schemes
        def run_search_schemes(query: str, top_k: int = 5, where_filter: Optional[dict[str, Any]] = None):
            matches = search_engine.search(query=query, top_k=top_k, where_filter=where_filter)
            return [
                {
                    "scheme_id": m.scheme_id,
                    "name": m.name,
                    "score": m.score,
                    "official_url": m.official_url,
                    "ministry": m.ministry,
                    "benefits": m.metadata.get("benefits_summary", ""),
                    "category_tags": m.metadata.get("category_tags", "")
                }
                for m in matches
            ]
        self.register("search_schemes", "Searches ChromaDB vector store for government schemes matching citizen query using dense semantic embeddings.", SearchSchemesInput, run_search_schemes)

        # 3. get_scheme_details
        def run_get_scheme_details(scheme_id: str):
            all_schemes = {s.id: s for s in load_all_schemes()}
            scheme = all_schemes.get(scheme_id)
            if not scheme:
                raise ValueError(f"Scheme ID '{scheme_id}' not found.")
            return scheme.model_dump()
        self.register("get_scheme_details", "Retrieves complete scheme definition including criteria, documents, and benefits.", GetSchemeDetailsInput, run_get_scheme_details)

        # 4. retrieve_scheme_evidence
        def run_retrieve_evidence(scheme_id: str):
            evidence = search_engine.get_scheme_evidence(scheme_id)
            if not evidence:
                raise ValueError(f"No indexed source evidence found for scheme '{scheme_id}'.")
            return evidence
        self.register("retrieve_scheme_evidence", "Retrieves raw source document text and official URL for verifying evidentiary grounding.", RetrieveEvidenceInput, run_retrieve_evidence)

        # 5. identify_information_gaps
        def run_identify_gaps(scheme_ids: list[str], profile_data: Optional[dict[str, Any]] = None):
            all_schemes = {s.id: s for s in load_all_schemes()}
            profile = _dict_to_profile(profile_data)
            targets = [all_schemes[sid] for sid in scheme_ids if sid in all_schemes]
            results = evaluate_all(profile, targets)
            
            missing_counter = {}
            almost_schemes = []
            for r in results:
                if r.status == EligibilityStatus.ALMOST:
                    almost_schemes.append(r.scheme_id)
                    for f in r.missing_fields:
                        missing_counter[f] = missing_counter.get(f, 0) + 1
            
            sorted_gaps = sorted(missing_counter.keys(), key=lambda k: missing_counter[k], reverse=True)
            return {
                "highest_impact_gap": sorted_gaps[0] if sorted_gaps else None,
                "all_gaps": sorted_gaps,
                "almost_schemes": almost_schemes
            }
        self.register("identify_information_gaps", "Identifies the missing citizen profile fields blocking eligibility for schemes.", IdentifyGapsInput, run_identify_gaps)

        # 6. ask_citizen_question
        def run_ask_question(field_name: str, language: str = "en"):
            from brain.asker import GapAsker
            asker = GapAsker()
            q = asker.generate_question(field_name, language=language)
            return {"field_name": field_name, "question": q, "language": language}
        self.register("ask_citizen_question", "Generates natural language clarifying question for citizen in Hindi or English.", AskCitizenInput, run_ask_question)

        # 7. verify_official_source
        def run_verify_source(url: str):
            res = verifier.check_portal(url)
            return res
        self.register("verify_official_source", "Tests live HTTP reachability and WAF protection of official government portal.", VerifyOfficialSourceInput, run_verify_source)

        # 8. compare_eligibility
        def run_compare_eligibility(profile_data: Optional[dict[str, Any]] = None, scheme_ids: Optional[list[str]] = None):
            from knowledge.matcher import SchemeMatcher
            all_schemes = load_all_schemes()
            if scheme_ids:
                targets = [s for s in all_schemes if s.id in scheme_ids]
            else:
                targets = all_schemes
            profile = _dict_to_profile(profile_data)
            matcher = SchemeMatcher()
            if scheme_ids:
                if matcher.decision_mode == "rules" or not matcher.llm_matcher.llm.is_available():
                    results = evaluate_all(profile, targets)
                else:
                    verdicts = matcher.llm_matcher.evaluate_all_grounded(profile, targets)
                    results = [matcher._verdict_to_match_result(v, targets) for v in verdicts]
            else:
                if matcher.decision_mode != "rules" and not matcher.llm_matcher.llm.is_available():
                    results = evaluate_all(profile, targets)
                else:
                    results = matcher.match(profile)
            return [r.model_dump() for r in results]
        self.register("compare_eligibility", "Evaluates citizen facts against scheme criteria using LLM grounding (or rules fallback).", CompareEligibilityInput, run_compare_eligibility)

        # 9. check_required_documents
        def run_check_documents(scheme_id: str, available_documents: list[str]):
            all_schemes = {s.id: s for s in load_all_schemes()}
            scheme = all_schemes.get(scheme_id)
            if not scheme:
                raise ValueError(f"Scheme ID '{scheme_id}' not found.")
            
            avail_lower = {d.lower().strip() for d in available_documents}
            missing = []
            ready = []
            for doc in scheme.documents_required:
                if any(avail in doc.lower() for avail in avail_lower):
                    ready.append(doc)
                else:
                    missing.append(doc)
            return {
                "scheme_id": scheme_id,
                "all_required": scheme.documents_required,
                "ready_documents": ready,
                "missing_documents": missing,
                "is_complete": len(missing) == 0
            }
        self.register("check_required_documents", "Checks whether citizen has all mandatory documents for a scheme application.", CheckDocumentsInput, run_check_documents)

        # 10. prepare_application_checklist
        def run_prepare_checklist(scheme_id: str):
            all_schemes = {s.id: s for s in load_all_schemes()}
            scheme = all_schemes.get(scheme_id)
            if not scheme:
                raise ValueError(f"Scheme ID '{scheme_id}' not found.")
            return {
                "scheme_id": scheme_id,
                "scheme_name": scheme.name,
                "documents_checklist": scheme.documents_required,
                "submission_url": scheme.official_url,
                "action_guidance": "Download prefilled application PDF and submit at official portal or nearest CSC."
            }
        self.register("prepare_application_checklist", "Builds actionable application checklist with required documents and portal URL.", ApplicationChecklistInput, run_prepare_checklist)

        # 11. generate_application_document
        def run_generate_doc(scheme_id: str, profile_data: Optional[dict[str, Any]] = None):
            all_schemes = {s.id: s for s in load_all_schemes()}
            scheme = all_schemes.get(scheme_id)
            if not scheme:
                raise ValueError(f"Scheme ID '{scheme_id}' not found.")
            profile = _dict_to_profile(profile_data)
            
            match = MatchResult(
                scheme_id=scheme.id,
                scheme_name=scheme.name,
                status=EligibilityStatus.ELIGIBLE,
                official_url=scheme.official_url,
                documents_required=scheme.documents_required,
            )
            pdf_path = generate_application_pdf(profile, match)
            return {
                "scheme_id": scheme_id,
                "pdf_path": str(pdf_path),
                "filename": pdf_path.name,
                "size_bytes": pdf_path.stat().st_size
            }
        self.register("generate_application_document", "Generates pre-filled official application PDF with provenance tags.", GenerateApplicationDocInput, run_generate_doc)

        # 12. create_application_task
        def run_create_task(scheme_id: str, citizen_id: str = "active_citizen", notes: str = ""):
            all_schemes = {s.id: s for s in load_all_schemes()}
            scheme = all_schemes.get(scheme_id)
            scheme_name = scheme.name if scheme else scheme_id
            portal = scheme.official_url if scheme else ""
            req_docs = scheme.documents_required if scheme else []
            task = app_tracker.create_task(
                citizen_id=citizen_id,
                scheme_id=scheme_id,
                scheme_name=scheme_name,
                documents_ready=[],
                documents_missing=req_docs,
                status="DRAFT",
                official_portal_url=portal,
                notes=notes,
            )
            return task
        self.register("create_application_task", "Creates a persistent application preparation task.", CreateApplicationTaskInput, run_create_task)

        # 13. update_application_status
        def run_update_status(task_id: str, status: str, notes: str = ""):
            try:
                updated = app_tracker.update_task_status(task_id, status=status, notes=notes)
                return updated
            except Exception:
                return {
                    "task_id": task_id,
                    "status": status,
                    "notes": notes,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
        self.register("update_application_status", "Updates the status of an ongoing scheme application task.", UpdateApplicationStatusInput, run_update_status)

        # 14. save_agent_memory
        def run_save_memory(key: str, value: Any):
            if isinstance(value, dict):
                profile = CitizenProfile.model_validate(value)
            elif isinstance(value, CitizenProfile):
                profile = value
            else:
                profile = CitizenProfile()
            memory_store.save_profile(key, profile)
            return {"key": key, "saved": True}
        self.register("save_agent_memory", "Saves state or citizen profile into SQLite persistent store.", SaveMemoryInput, run_save_memory)

        # 15. retrieve_agent_memory
        def run_retrieve_memory(key: str):
            profile = memory_store.get_profile(key)
            return {"key": key, "profile": profile.model_dump() if profile else None}
        self.register("retrieve_agent_memory", "Retrieves stored citizen profile from SQLite persistent memory.", RetrieveMemoryInput, run_retrieve_memory)

        # 16. get_vault_documents
        def run_get_vault_documents(user_id: str = "active_citizen"):
            vault = DocumentVault()
            docs = vault.list_documents(user_id=user_id)
            return [d.model_dump() for d in docs]
        self.register("get_vault_documents", "Inspects citizen's verified identity and revenue documents stored in the encrypted vault.", GetVaultDocumentsInput, run_get_vault_documents)

        # 17. draft_notification
        def run_draft_notification(
            user_id: str = "active_citizen",
            event_type: str = "SCHEME_UPDATE",
            recipient: str = "",
            channel: str = "email",
            language: str = "en",
            context_data: Optional[dict[str, Any]] = None,
        ):
            notifier = NotificationService()
            req = DraftGenerationRequest(
                user_id=user_id,
                event_type=event_type,
                recipient=recipient,
                channel=channel,
                language=language,
                context_data=context_data or {},
            )
            draft = notifier.draft_message(req)
            return draft.model_dump()
        self.register("draft_notification", "Drafts an AI personalized alert or reminder in citizen's language awaiting human approval.", DraftNotificationInput, run_draft_notification)

        # 18. explain_rejection
        def run_explain_rejection(
            scheme_id: str,
            profile_data: Optional[dict[str, Any]] = None,
            language: str = "en",
        ):
            from knowledge.llm_matcher import LLMMatcher
            all_schemes = {s.id: s for s in load_all_schemes()}
            scheme = all_schemes.get(scheme_id)
            if not scheme:
                raise ValueError(f"Scheme ID '{scheme_id}' not found.")
            profile = _dict_to_profile(profile_data)
            matcher = LLMMatcher()
            verdict = matcher.evaluate_scheme_grounded(profile, scheme)
            explanation = matcher.explain_rejection(verdict, language=language)
            return explanation.model_dump()
        self.register("explain_rejection", "Provides compassionate, clear plain-language explanation of why a citizen does not qualify.", ExplainRejectionInput, run_explain_rejection)

        # 19. recommend_next_best
        def run_recommend_next_best(
            ineligible_scheme_id: str,
            profile_data: Optional[dict[str, Any]] = None,
            top_k: int = 3,
        ):
            from knowledge.llm_matcher import LLMMatcher
            profile = _dict_to_profile(profile_data)
            matcher = LLMMatcher()
            recs = matcher.recommend_next_best(profile, ineligible_scheme_id=ineligible_scheme_id, top_k=top_k)
            return [r.model_dump() for r in recs]
        self.register("recommend_next_best", "Recommends closest matching alternative government schemes for ineligible applicants.", RecommendNextBestInput, run_recommend_next_best)

