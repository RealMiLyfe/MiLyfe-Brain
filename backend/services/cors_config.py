"""
CORS configuration with production lockdown for MiLyfe Brain.

Development: Allow all origins (CORS_ALLOW_ALL=true)
Production: Restrict to specific allowed origins

Configuration via environment variables:
    CORS_ALLOW_ALL=false
    CORS_ALLOWED_ORIGINS=https://milyfe.ai,https://app.milyfe.ai
    CORS_ALLOWED_METHODS=GET,POST,PUT,DELETE,OPTIONS,PATCH
    CORS_ALLOWED_HEADERS=*
    CORS_ALLOW_CREDENTIALS=true
    CORS_MAX_AGE=86400
"""

import os
from dataclasses import dataclass, field
from typing import List


@dataclass
class CORSConfig:
    """CORS configuration."""
    allow_all: bool = False
    allowed_origins: List[str] = field(default_factory=list)
    allowed_methods: List[str] = field(default_factory=lambda: ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"])
    allowed_headers: List[str] = field(default_factory=lambda: ["*"])
    allow_credentials: bool = True
    max_age: int = 86400  # 24 hours


def get_cors_config() -> CORSConfig:
    """Load CORS configuration from environment."""
    allow_all = os.getenv("CORS_ALLOW_ALL", "true").lower() == "true"

    # Parse origins
    origins_str = os.getenv("CORS_ALLOWED_ORIGINS", "")
    if origins_str:
        allowed_origins = [o.strip() for o in origins_str.split(",") if o.strip()]
    elif allow_all:
        allowed_origins = ["*"]
    else:
        # Secure default: only localhost variants
        allowed_origins = [
            "http://localhost:3000",
            "http://localhost:8200",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8200",
        ]

    # Parse methods
    methods_str = os.getenv("CORS_ALLOWED_METHODS", "")
    if methods_str:
        allowed_methods = [m.strip() for m in methods_str.split(",")]
    else:
        allowed_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]

    # Parse headers
    headers_str = os.getenv("CORS_ALLOWED_HEADERS", "*")
    allowed_headers = [h.strip() for h in headers_str.split(",")]

    return CORSConfig(
        allow_all=allow_all,
        allowed_origins=allowed_origins,
        allowed_methods=allowed_methods,
        allowed_headers=allowed_headers,
        allow_credentials=os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true",
        max_age=int(os.getenv("CORS_MAX_AGE", "86400")),
    )


def apply_cors(app, config: CORSConfig = None):
    """Apply CORS middleware to FastAPI app."""
    from fastapi.middleware.cors import CORSMiddleware

    if config is None:
        config = get_cors_config()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.allowed_origins,
        allow_credentials=config.allow_credentials,
        allow_methods=config.allowed_methods,
        allow_headers=config.allowed_headers,
        max_age=config.max_age,
    )
