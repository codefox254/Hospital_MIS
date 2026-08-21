"""
Roles TRD §3.3/§4.3 name explicitly as privileged (MFA mandatory). This is a
placeholder catalogue, not the BRD's full role list (docs/README.md flags the
missing BRD) — extend as later milestones confirm more privileged roles.
"""

PRIVILEGED_ROLE_NAMES = frozenset(
    {
        "Administrator",
        "Finance Manager",
        "IT Administrator",
        "Medical Director",
        "Insurance Officer",
        "Super Admin",
    }
)
