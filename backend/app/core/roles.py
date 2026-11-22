"""Roles and which screens each one may open (docs/spec/04_roles_y_pantallas.md → "Pantallas").

This is the single source of truth: the API sends the list to the frontend in /api/auth/me,
and the API endpoints check roles with `require_role` (app/core/deps.py).
"""

OWNER, COORDINATOR, PHYSICIAN, CAREGIVER, FAMILY = "owner", "coordinator", "physician", "caregiver", "family"
ALL_ROLES = (OWNER, COORDINATOR, PHYSICIAN, CAREGIVER, FAMILY)

# First screen after login.
HOME_BY_ROLE: dict[str, str] = {
    OWNER: "/panorama",
    COORDINATOR: "/tablero",
    PHYSICIAN: "/reportes-voz",
    CAREGIVER: "/mis-visitas",
    FAMILY: "/familia",
}

# Screen route → roles allowed to open it.
SCREEN_ROLES: dict[str, tuple[str, ...]] = {
    "/tablero": (COORDINATOR,),
    "/aprobaciones": (COORDINATOR,),
    "/pacientes": (COORDINATOR, PHYSICIAN),
    "/personal": (COORDINATOR,),
    "/mis-visitas": (CAREGIVER,),
    "/familia": (FAMILY,),
    "/voz": (FAMILY, CAREGIVER),
    "/reportes-voz": (PHYSICIAN,),
    "/panorama": (COORDINATOR, OWNER),
    "/simulacion": (COORDINATOR, OWNER),
    "/contingencia": (COORDINATOR, OWNER),
    "/negocio": (OWNER,),
    "/privacidad": ALL_ROLES,
    "/demo": (OWNER,),
}


def screens_for(role: str) -> list[str]:
    """Screens a role may open, in menu order."""
    return [path for path, roles in SCREEN_ROLES.items() if role in roles]
