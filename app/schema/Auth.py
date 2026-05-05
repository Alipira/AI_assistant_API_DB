from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


@dataclass(frozen=True)
class AuthContext:
    """
    Information about the current user/session.

    access_token:
        User access token from ur auth system. Prefer JWT/OAuth2 bearer token.
    user_id:
        Stable user identifier from  auth system.
    tenant_id:
        Optional tenant/org identifier.
    roles:
        Optional roles known by  auth system.
    scopes:
        Optional scopes/permissions known by auth system.
    """
    access_token: str
    user_id: str
    # tenant_id is disabled — backend does not support multi-tenancy
    # tenant_id: Optional[str] = None
    # roles: Tuple[str, ...] = ()
    # scopes: Tuple[str, ...] = ()


@dataclass(frozen=True)
class ActionSpec:
    endpoint: str
    method: str
    required_scope: Optional[str] = None
    required_role: Optional[str] = None
    allowed_params: Tuple[str, ...] = ()
    description: str = ""
    # Optional body template for POST endpoints
    # Use "{param_name}" as placeholder for values the LLM provides
    body_template: Optional[Dict[str, Any]] = None
