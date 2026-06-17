#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# MiLyfe Brain — Docker Stack Validation Script
# Run this after `docker compose up -d` to verify all services are healthy.
# ═══════════════════════════════════════════════════════════════════════════════

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "═══════════════════════════════════════════════════════"
echo " MiLyfe Brain — Docker Validation"
echo "═══════════════════════════════════════════════════════"
echo ""

BACKEND_URL="${BACKEND_URL:-http://localhost:8200}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"
CHROMADB_URL="${CHROMADB_URL:-http://localhost:8400}"
REDIS_PORT="${REDIS_PORT:-6479}"

PASS=0
FAIL=0

check() {
    local name="$1"
    local cmd="$2"
    printf "  %-30s" "$name"
    if eval "$cmd" > /dev/null 2>&1; then
        echo -e "${GREEN}PASS${NC}"
        PASS=$((PASS + 1))
    else
        echo -e "${RED}FAIL${NC}"
        FAIL=$((FAIL + 1))
    fi
}

echo "1. Service Health Checks"
echo "────────────────────────────────────────────────────"
check "Backend /health" "curl -sf ${BACKEND_URL}/health"
check "Backend /docs" "curl -sf ${BACKEND_URL}/docs"
check "Frontend" "curl -sf ${FRONTEND_URL}"
check "ChromaDB heartbeat" "curl -sf ${CHROMADB_URL}/api/v1/heartbeat"
check "Redis ping" "redis-cli -p ${REDIS_PORT} ping 2>/dev/null || docker exec milyfe-redis redis-cli ping"

echo ""
echo "2. API Endpoint Validation"
echo "────────────────────────────────────────────────────"
check "GET /api/agents/roles" "curl -sf ${BACKEND_URL}/api/agents/roles"
check "GET /api/queue/status" "curl -sf ${BACKEND_URL}/api/queue/status"
check "GET /api/settings/" "curl -sf ${BACKEND_URL}/api/settings/"
check "GET /health/circuits" "curl -sf ${BACKEND_URL}/health/circuits"

echo ""
echo "3. Playbook Integration Test"
echo "────────────────────────────────────────────────────"
# Create a playbook
RESPONSE=$(curl -sf -X POST "${BACKEND_URL}/api/playbooks/" \
    -H "Content-Type: application/json" \
    -d '{"title": "Validation Test", "description": "Docker validation test playbook", "raw_text": "- List workspace files\n- Report results"}' \
    2>/dev/null)
if [ $? -eq 0 ] && echo "$RESPONSE" | grep -q "id"; then
    PLAYBOOK_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null || echo "")
    if [ -n "$PLAYBOOK_ID" ]; then
        echo -e "  Playbook created:              ${GREEN}PASS${NC} (id: ${PLAYBOOK_ID:0:8}...)"
        PASS=$((PASS + 1))
        
        # Check status
        sleep 2
        check "Playbook status retrieval" "curl -sf ${BACKEND_URL}/api/playbooks/${PLAYBOOK_ID}/status"
    else
        echo -e "  Playbook created:              ${RED}FAIL${NC} (no ID in response)"
        FAIL=$((FAIL + 1))
    fi
else
    echo -e "  Playbook creation:             ${RED}FAIL${NC}"
    FAIL=$((FAIL + 1))
fi

echo ""
echo "═══════════════════════════════════════════════════════"
echo -e " Results: ${GREEN}${PASS} passed${NC}, ${RED}${FAIL} failed${NC}"
echo "═══════════════════════════════════════════════════════"

if [ $FAIL -gt 0 ]; then
    echo -e "${YELLOW}Some checks failed. Run 'docker compose logs' for details.${NC}"
    exit 1
else
    echo -e "${GREEN}All checks passed! MiLyfe Brain is running correctly.${NC}"
    exit 0
fi
