#!/usr/bin/env python3
"""
Export OpenAPI spec from running FastAPI application.

Usage:
    python scripts/export_openapi.py > docs/api/openapi.yaml

Or in CI:
    python scripts/export_openapi.py --format yaml --output docs/api/openapi.yaml
    python scripts/export_openapi.py --format json --output docs/api/openapi.json
"""

import argparse
import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


def get_openapi_spec():
    """Extract OpenAPI spec from FastAPI app."""
    try:
        from main import app
        return app.openapi()
    except ImportError:
        print("Error: Cannot import FastAPI app. Run from project root.", file=sys.stderr)
        sys.exit(1)


def export_yaml(spec: dict) -> str:
    """Convert spec to YAML format."""
    try:
        import yaml
        return yaml.dump(spec, default_flow_style=False, sort_keys=False, allow_unicode=True)
    except ImportError:
        print("Error: PyYAML not installed. Install with: pip install pyyaml", file=sys.stderr)
        sys.exit(1)


def export_json(spec: dict) -> str:
    """Convert spec to JSON format."""
    return json.dumps(spec, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description="Export OpenAPI specification")
    parser.add_argument(
        "--format", "-f",
        choices=["yaml", "json"],
        default="yaml",
        help="Output format (default: yaml)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Output file path (default: stdout)"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate the spec after export"
    )

    args = parser.parse_args()

    spec = get_openapi_spec()

    if args.format == "yaml":
        content = export_yaml(spec)
    else:
        content = export_json(spec)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content)
        print(f"OpenAPI spec exported to: {output_path}", file=sys.stderr)
    else:
        print(content)

    if args.validate:
        try:
            from openapi_spec_validator import validate
            validate(spec)
            print("Validation: PASSED", file=sys.stderr)
        except ImportError:
            print("Warning: openapi-spec-validator not installed. Skipping validation.", file=sys.stderr)
        except Exception as e:
            print(f"Validation: FAILED - {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
