"""One-time interactive Garmin login. Prompts for the password (and MFA if
Garmin asks), then dumps tokens to ~/.garminconnect so the app and backfill
authenticate from cache without storing the password.

    python scripts/garmin_login.py            # log in, cache tokens locally
    python scripts/garmin_login.py --export   # ALSO print the GARMIN_TOKENS blob

`--export` prints the session blob to paste into your host's GARMIN_TOKENS env
var (see DEPLOY.md). A deployed container needs it: its filesystem is ephemeral,
so there is no cached token store, and a fresh SSO login would block forever on
an MFA prompt with no stdin to answer it.

If tokens are already cached locally, --export reuses them — no re-login needed.

The blob is a live credential. Treat it like a password: paste it straight into
your host's secret store, don't commit it, don't share it.
"""

import getpass
import sys

from garminconnect import Garmin

from jim.config import settings
from jim.tools.garmin import MIN_TOKEN_BLOB_CHARS, TOKEN_STORE

export = "--export" in sys.argv


def _print_blob(g: Garmin) -> None:
    blob = g.client.dumps()
    if len(blob) <= MIN_TOKEN_BLOB_CHARS:
        print(
            f"\n!! The token blob is only {len(blob)} chars, but garminconnect only"
            f" treats a string >{MIN_TOKEN_BLOB_CHARS} chars as token data (shorter"
            " values are read as a file path). This session won't load remotely.",
            file=sys.stderr,
        )
    print("\n--- GARMIN_TOKENS (secret — paste into your host's env, don't commit) ---")
    print(blob)
    print("--- end ---")


g = Garmin(settings().garmin_email, "")
if export:
    try:  # reuse the cached session if there is one; no need to re-enter a password
        g.login(TOKEN_STORE)
        print(f"Reusing cached tokens from {TOKEN_STORE} (logged in as {g.get_full_name()}).")
        _print_blob(g)
        sys.exit(0)
    except Exception:
        print("No usable cached session — logging in fresh.")

email = settings().garmin_email or input("Garmin email: ").strip()
password = getpass.getpass(f"Garmin password for {email}: ")

print("Logging in (an MFA prompt may follow)...")
g = Garmin(email, password)
g.login(TOKEN_STORE)  # prompts for MFA on stdin when required, then caches tokens

print(f"OK — logged in as {g.get_full_name()}. Tokens cached at {TOKEN_STORE}.")
if export:
    _print_blob(g)
