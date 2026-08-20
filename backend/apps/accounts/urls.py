"""
Auth endpoints (POST /api/v1/auth/token/, /refresh/) and MFA/break-glass
routes land in the auth/permission-engine milestone (Milestone 0, PR 2) — this
file exists now so config.urls' `include("apps.accounts.urls")` is stable
across that PR rather than being added as a new include later.
"""

app_name = "accounts"

urlpatterns = []
