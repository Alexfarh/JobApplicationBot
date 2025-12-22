# Remote Browser Session (noVNC)

## Purpose
Allow user to authenticate (Workday login, OTP) from phone
inside the SAME browser session controlled by Playwright.

## Stack
- Xvfb
- Chromium (headed)
- Window manager (openbox/fluxbox)
- x11vnc
- noVNC web client

## Rules
- One session per run
- User access via signed URL
- Must be behind dashboard auth
- HTTPS required

## NEVER
- Open auth flows in user's local browser
- Create ATS accounts automatically
