"""One-time interactive Garmin login. Prompts for the password (and MFA if
Garmin asks), then dumps tokens to ~/.garminconnect so the app and backfill
authenticate from cache without storing the password. Run: python scripts/garmin_login.py"""

import getpass

from garminconnect import Garmin

from jim.config import settings
from jim.tools.garmin import TOKEN_STORE

email = settings().garmin_email
if not email:
    email = input("Garmin email: ").strip()
password = getpass.getpass(f"Garmin password for {email}: ")

print("Logging in (an MFA prompt may follow)...")
g = Garmin(email, password)
g.login(TOKEN_STORE)  # prompts for MFA on stdin when required, then caches tokens

name = g.get_full_name()
print(f"OK — logged in as {name}. Tokens cached at {TOKEN_STORE}.")
