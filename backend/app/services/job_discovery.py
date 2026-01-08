"""
Job discovery service module.
Handles ATS detection, job feed fetching, normalization, ranking, and filtering for job discovery endpoint.
"""
from typing import List, Dict, Any
import aiohttp
from app.schemas.job import JobDiscoveryResponse
import asyncio
from typing import Optional
from datetime import datetime

GREENHOUSE_BASE = "https://boards-api.greenhouse.io/v1/boards"

# # Placeholder for main job discovery function
# async def discover_jobs_for_user(user_profile: Dict[str, Any], filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
#     """
#     Discover jobs for a user based on their profile and filters.
#     Steps:
#     1. Get target companies from user_profile
#     2. Detect ATS type for each company
#     3. Fetch job postings from ATS feeds
#     4. Normalize and dedupe postings
#     5. Score/rank jobs against user profile
#     6. Filter and return ranked list
#     """
#     # TODO: Implement discovery logic
#     return []

async def fetch_greenhouse_jobs(
    board_token: str,
    session: aiohttp.ClientSession,
    timeout_s: int = 15
) -> List[Dict[str, Any]]:
    """Fetch jobs from a Greenhouse board via public API."""
    import logging
    import ssl
    logger = logging.getLogger(__name__)
    
    print(f"DEBUG: fetch_greenhouse_jobs called with board_token={board_token}", flush=True)
    print(f"DEBUG: session={session}, connector={session.connector}", flush=True)
    print(f"DEBUG: connector type={type(session.connector)}", flush=True)
    print(f"DEBUG: connector._ssl_context={getattr(session.connector, '_ssl_context', 'NOT SET')}", flush=True)
    logger.info(f"DEBUG: fetch_greenhouse_jobs called with board_token={board_token}")
    logger.info(f"DEBUG: session connector: {session.connector}")
    logger.info(f"DEBUG: session connector SSL: {getattr(session.connector, '_ssl_context', 'NOT SET')}")
    
    url = f"{GREENHOUSE_BASE}/{board_token}/jobs"
    headers = {"User-Agent": "JobApplicationBot/1.0 (job discovery)"}
    print(f"DEBUG: URL = {url}", flush=True)
    
    for attempt in range(2):
        try:
            print(f"DEBUG: Attempt {attempt+1} to fetch {board_token}", flush=True)
            timeout = aiohttp.ClientTimeout(total=timeout_s)
            print(f"DEBUG: About to call session.get with timeout={timeout}", flush=True)
            async with session.get(url, headers=headers, timeout=timeout) as resp:
                print(f"DEBUG: Got response object for {board_token}", flush=True)
                body_text = await resp.text(errors="ignore")
                
                print(f"DEBUG: Got response status={resp.status} for {board_token}", flush=True)
                logger.info(
                    f"[{board_token}] status={resp.status} content_type={resp.headers.get('Content-Type')} "
                    f"body_head={body_text[:200]!r}"
                )
                
                if resp.status != 200:
                    print(f"DEBUG: Non-200 status {resp.status}, returning []", flush=True)
                    logger.warning(f"[{board_token}] Non-200 status, returning []")
                    return []
                
                try:
                    print(f"DEBUG: Parsing JSON for {board_token}", flush=True)
                    data = await resp.json()
                    print(f"DEBUG: JSON parsed successfully for {board_token}", flush=True)
                except Exception as e:
                    print(f"DEBUG: JSON parse error: {type(e).__name__}: {e}", flush=True)
                    logger.error(f"[{board_token}] JSON parse failed: {type(e).__name__}: {e}")
                    return []
                
                jobs = data.get("jobs", [])
                logger.info(f"[{board_token}] jobs_count={len(jobs)}")
                print(f"DEBUG: Returning {len(jobs)} jobs for {board_token}", flush=True)
                return jobs if isinstance(jobs, list) else []
                
        except Exception as e:
            print(f"DEBUG: Exception on attempt {attempt+1} for {board_token}: {type(e).__name__}: {str(e)[:100]}", flush=True)
            import traceback
            print(f"DEBUG: Full traceback:\n{traceback.format_exc()}", flush=True)
            logger.error(f"[{board_token}] Error (attempt {attempt+1}/2): {type(e).__name__}: {str(e)[:200]}", exc_info=True)
            if attempt == 0:
                await asyncio.sleep(0.5)
            else:
                print(f"DEBUG: Giving up after 2 attempts for {board_token}", flush=True)
                logger.error(f"[{board_token}] Giving up after 2 attempts")
                return []


def normalize_greenhouse_job(raw_job: dict, company_name: str) -> Optional[JobDiscoveryResponse]:
    title = raw_job.get("title")
    apply_url = raw_job.get("absolute_url")
    if not title or not apply_url:
        return None  # skip malformed jobs
    # Parse posted_at as datetime if present
    posted_at_raw = raw_job.get("updated_at")
    posted_at = None
    if posted_at_raw:
        try:
            posted_at = datetime.fromisoformat(posted_at_raw.replace("Z", "+00:00"))
        except Exception:
            posted_at = None
    return JobDiscoveryResponse(
        company_name=company_name,
        job_title=title,
        location_text=(raw_job.get("location") or {}).get("name"),
        employment_type=None,
        work_mode=None,
        description_raw=raw_job.get("content"),   # sometimes present; otherwise None
        description_clean=None,
        apply_url=apply_url,
        ats_type="greenhouse",
        inferred_role_category=None,
        inferred_seniority=None,
        salary_min=None,
        salary_max=None,
        salary_unit=None,
        salary_currency=None,
        salary_source="unknown",
        match_score=None,
        salary_meets_expectations=None,
        mismatch_reasons=[],
        source_company_url=None,
        posted_at=posted_at,
    )


async def discover_greenhouse_for_targets(targets: List[Dict[str, str]]) -> List[JobDiscoveryResponse]:
    out: List[JobDiscoveryResponse] = []
    async with aiohttp.ClientSession() as session:
        for t in targets:
            board_token = t["board_token"]
            company_name = t["company_name"]
            raw_jobs = await fetch_greenhouse_jobs(board_token, session)
            for rj in raw_jobs:
                norm = normalize_greenhouse_job(rj, company_name)
                if norm:
                    out.append(norm)
    return out
