"""MiLyfe Brain — Brain/CEO Feature Routes (analytics, onboarding, marketplace, voice, etc.)."""

from __future__ import annotations

from fastapi import APIRouter, File, UploadFile

router = APIRouter()


# ─── Onboarding ───────────────────────────────────────────────

@router.get("/onboarding/status")
async def onboarding_status():
    from services.onboarding import onboarding_service
    return await onboarding_service.get_status()

@router.get("/onboarding/system-info")
async def system_info():
    from services.onboarding import onboarding_service
    return await onboarding_service.get_system_info()

@router.get("/onboarding/recommend-models")
async def recommend_models():
    from services.onboarding import onboarding_service
    return await onboarding_service.recommend_models()

@router.get("/onboarding/tutorial")
async def get_tutorial():
    from services.onboarding import onboarding_service
    return onboarding_service.get_tutorial_steps()


# ─── Analytics ────────────────────────────────────────────────

@router.get("/analytics/overview")
async def analytics_overview(days: int = 30):
    from services.analytics import analytics_service
    return await analytics_service.get_overview(days)

@router.get("/analytics/agents")
async def agent_performance():
    from services.analytics import analytics_service
    return await analytics_service.get_agent_performance()


# ─── Marketplace ──────────────────────────────────────────────

@router.get("/marketplace")
async def marketplace_index():
    from services.marketplace import marketplace_service
    return await marketplace_service.get_index()

@router.get("/marketplace/search")
async def marketplace_search(query: str, category: str = ""):
    from services.marketplace import marketplace_service
    return await marketplace_service.search(query, category)

@router.post("/marketplace/install/{playbook_id}")
async def install_playbook(playbook_id: str):
    from services.marketplace import marketplace_service
    return await marketplace_service.install_playbook(playbook_id)


# ─── Voice ────────────────────────────────────────────────────

@router.get("/voice/capabilities")
async def voice_capabilities():
    from services.voice_interface import voice_interface
    return voice_interface.get_capabilities()

@router.post("/voice/stt")
async def speech_to_text(file: UploadFile = File(...)):
    from services.voice_interface import voice_interface
    audio_data = await file.read()
    text = await voice_interface.speech_to_text(audio_data)
    return {"text": text}

@router.post("/voice/tts")
async def text_to_speech(text: str):
    from services.voice_interface import voice_interface
    from fastapi.responses import Response
    audio = await voice_interface.text_to_speech(text)
    if audio:
        return Response(content=audio, media_type="audio/wav")
    return {"error": "TTS not available"}


# ─── Reproducibility ─────────────────────────────────────────

@router.post("/reproducibility/export/{playbook_id}")
async def export_ci(playbook_id: str, format: str = "github_action"):
    from services.reproducibility import reproducibility_service
    content = await reproducibility_service.export_as_ci(playbook_id, format)
    return {"format": format, "content": content}

@router.post("/reproducibility/diff")
async def diff_runs(run_a: str, run_b: str):
    from services.reproducibility import reproducibility_service
    return await reproducibility_service.diff_runs(run_a, run_b)


# ─── Compliance ───────────────────────────────────────────────

@router.post("/compliance/scan-pii")
async def scan_pii(path: str):
    from services.compliance import compliance_service
    return await compliance_service.scan_file_for_pii(path)

@router.get("/compliance/licenses")
async def scan_licenses():
    from services.compliance import compliance_service
    return await compliance_service.scan_workspace_licenses()

@router.get("/compliance/lineage/{file_path:path}")
async def data_lineage(file_path: str):
    from services.compliance import compliance_service
    return await compliance_service.get_data_lineage(file_path)

@router.post("/compliance/retention")
async def apply_retention(max_age_days: int = 90):
    from services.compliance import compliance_service
    await compliance_service.apply_retention_policy(max_age_days)
    return {"applied": True, "max_age_days": max_age_days}


# ─── Memory Sharing ──────────────────────────────────────────

@router.get("/memory/shared/{space_id}")
async def get_shared_memory(space_id: str, category: str = ""):
    from services.memory_sharing import shared_memory
    return await shared_memory.read(space_id, category)

@router.get("/memory/knowledge")
async def query_knowledge(type: str = ""):
    from services.memory_sharing import knowledge_graph
    return await knowledge_graph.query(type=type)


# ─── Multi-User ──────────────────────────────────────────────

@router.get("/users")
async def list_users():
    from services.multi_user import multi_user_service
    return await multi_user_service.list_users()

@router.post("/users/create")
async def create_user(username: str, password: str, role: str = "user"):
    from services.multi_user import multi_user_service
    return await multi_user_service.create_user(username, password, role)

@router.post("/users/login")
async def login(username: str, password: str):
    from services.multi_user import multi_user_service
    token = await multi_user_service.authenticate(username, password)
    if token:
        return {"token": token}
    return {"error": "Invalid credentials"}
