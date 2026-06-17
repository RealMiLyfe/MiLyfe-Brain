"""
TLS/HTTPS configuration for MiLyfe Brain.

Supports three modes:
1. No TLS (development) - plain HTTP
2. Self-signed TLS (local testing) - auto-generated certs
3. Production TLS (via reverse proxy) - TLS terminated at ingress/ALB

Configuration via environment variables:
    TLS_ENABLED=true
    TLS_CERT_FILE=/certs/server.crt
    TLS_KEY_FILE=/certs/server.key
    TLS_CA_FILE=/certs/ca.crt (optional)
    TLS_AUTO_GENERATE=true (generate self-signed for local dev)
    FORCE_HTTPS=true (redirect HTTP to HTTPS)
"""

import os
import ssl
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class TLSConfig:
    """TLS configuration."""
    enabled: bool = False
    cert_file: Optional[str] = None
    key_file: Optional[str] = None
    ca_file: Optional[str] = None
    auto_generate: bool = False
    force_https: bool = False
    min_version: str = "TLSv1.2"


def get_tls_config() -> TLSConfig:
    """Load TLS configuration from environment."""
    return TLSConfig(
        enabled=os.getenv("TLS_ENABLED", "false").lower() == "true",
        cert_file=os.getenv("TLS_CERT_FILE"),
        key_file=os.getenv("TLS_KEY_FILE"),
        ca_file=os.getenv("TLS_CA_FILE"),
        auto_generate=os.getenv("TLS_AUTO_GENERATE", "false").lower() == "true",
        force_https=os.getenv("FORCE_HTTPS", "false").lower() == "true",
        min_version=os.getenv("TLS_MIN_VERSION", "TLSv1.2"),
    )


def generate_self_signed_cert(cert_dir: str = "/certs") -> tuple[str, str]:
    """Generate a self-signed certificate for local development.

    Returns:
        Tuple of (cert_path, key_path)
    """
    try:
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID
        import datetime
    except ImportError:
        raise RuntimeError("Install 'cryptography' package for TLS cert generation")

    cert_path = Path(cert_dir)
    cert_path.mkdir(parents=True, exist_ok=True)

    cert_file = cert_path / "server.crt"
    key_file = cert_path / "server.key"

    # Generate key
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    # Generate certificate
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "MiLyfe Brain (Development)"),
        x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
    ])

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow())
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.DNSName("*.milyfe.local"),
                x509.IPAddress(ipaddress_from_string("127.0.0.1")),
            ]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )

    # Write files
    key_file.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    cert_file.write_bytes(cert.public_bytes(serialization.Encoding.PEM))

    return str(cert_file), str(key_file)


def ipaddress_from_string(addr: str):
    """Convert string IP to ipaddress object."""
    import ipaddress
    return ipaddress.IPv4Address(addr)


def create_ssl_context(config: TLSConfig) -> Optional[ssl.SSLContext]:
    """Create an SSL context for uvicorn."""
    if not config.enabled:
        return None

    if config.auto_generate and (not config.cert_file or not Path(config.cert_file).exists()):
        config.cert_file, config.key_file = generate_self_signed_cert()

    if not config.cert_file or not config.key_file:
        raise ValueError("TLS enabled but no cert/key files specified")

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)

    # Set minimum version
    if config.min_version == "TLSv1.3":
        ctx.minimum_version = ssl.TLSVersion.TLSv1_3
    else:
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2

    # Load certificate chain
    ctx.load_cert_chain(config.cert_file, config.key_file)

    # Load CA if specified (for client cert verification)
    if config.ca_file:
        ctx.load_verify_locations(config.ca_file)
        ctx.verify_mode = ssl.CERT_OPTIONAL

    # Security settings
    ctx.set_ciphers("ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20")
    ctx.options |= ssl.OP_NO_SSLv2
    ctx.options |= ssl.OP_NO_SSLv3
    ctx.options |= ssl.OP_NO_TLSv1
    ctx.options |= ssl.OP_NO_TLSv1_1

    return ctx


def get_uvicorn_ssl_kwargs(config: Optional[TLSConfig] = None) -> dict:
    """Get SSL kwargs for uvicorn.run()."""
    if config is None:
        config = get_tls_config()

    if not config.enabled:
        return {}

    if config.auto_generate and (not config.cert_file or not Path(config.cert_file).exists()):
        config.cert_file, config.key_file = generate_self_signed_cert()

    return {
        "ssl_certfile": config.cert_file,
        "ssl_keyfile": config.key_file,
        "ssl_ca_certs": config.ca_file,
    }


class HTTPSRedirectMiddleware:
    """Middleware to redirect HTTP to HTTPS."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            # Check X-Forwarded-Proto (set by reverse proxy)
            forwarded_proto = headers.get(b"x-forwarded-proto", b"").decode()
            scheme = scope.get("scheme", "http")

            if forwarded_proto == "http" or (not forwarded_proto and scheme == "http"):
                # Redirect to HTTPS
                host = headers.get(b"host", b"localhost").decode()
                path = scope.get("path", "/")

                response_headers = [
                    (b"location", f"https://{host}{path}".encode()),
                    (b"content-length", b"0"),
                ]

                await send({
                    "type": "http.response.start",
                    "status": 301,
                    "headers": response_headers,
                })
                await send({"type": "http.response.body", "body": b""})
                return

        await self.app(scope, receive, send)
