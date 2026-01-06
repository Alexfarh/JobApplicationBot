import asyncio
from playwright.async_api import async_playwright
from sqlalchemy import select
from app.models.job_posting import JobPosting
from app.models.user import User
import os

async def launch_remote_browser():
    """
    Launch a Chromium browser with remote debugging enabled for noVNC access.
    Returns: (browser, ws_endpoint)
    """
    from playwright.async_api import async_playwright
    # Use a persistent context for session sharing
    user_data_dir = os.environ.get("PLAYWRIGHT_USER_DATA_DIR", "/tmp/playwright-user-data")
    remote_port = int(os.environ.get("PLAYWRIGHT_REMOTE_PORT", "9222"))
    p = await async_playwright().start()
    browser = await p.chromium.launch_persistent_context(
        user_data_dir,
        headless=False,  # Must be False for noVNC
        args=[f"--remote-debugging-port={remote_port}"]
    )
    # Playwright does not expose ws endpoint directly, but we know the port
    ws_endpoint = f"ws://localhost:{remote_port}/devtools/browser"
    print(f"[noVNC] Browser launched for remote access at {ws_endpoint}")
    return browser, ws_endpoint

async def autofill_job_application(task, db):
	"""
	Launches a browser, navigates to the job_url from the task's job, and prepares for autofill.
	Args:
		task: ApplicationTask SQLAlchemy object (must have job_id)
		db: AsyncSession for DB access
	Returns:
		None (for now)
	"""
	# Fetch job from DB
	result = await db.execute(select(JobPosting).where(JobPosting.id == task.job_id))
	job = result.scalar_one_or_none()
	
	if not job:
		raise ValueError(f"No job found for task.job_id={task.job_id}")
	job_url = job.job_url
	
	# Fetch user from DB
	result = await db.execute(select(User).where(User.id == job.user_id))
	user = result.scalar_one_or_none()
	
	if not user:
		raise ValueError(f"No user found for job.user_id={job.user_id}")
	user_profile = user  # Use user object or extract fields as needed

	async with async_playwright() as p:
		browser = await p.chromium.launch(headless=True)
		page = await browser.new_page()
		print(f"Navigating to {job_url}")
		await page.goto(job_url)
		# TODO: Add autofill logic here using user_profile
		# Example: await page.fill('input[name=\"firstName\"]', user_profile.full_name)
		# ...
		await browser.close()
