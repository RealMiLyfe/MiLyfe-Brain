"""Unit tests for the playbook parser."""

import pytest
import json
from graphs.playbook_parser import PlaybookParser
from models.schemas import AgentRole, TaskComplexity


@pytest.fixture
def parser():
    return PlaybookParser()



class TestJsonParsing:
    """Test JSON pass-through parsing."""

    @pytest.mark.asyncio
    async def test_json_array_of_dicts(self, parser):
        raw = json.dumps([
            {"description": "Research the topic", "agent_role": "researcher"},
            {"description": "Write the code", "agent_role": "coder"},
        ])
        steps = await parser.parse(raw)
        assert len(steps) == 2
        assert steps[0].description == "Research the topic"
        assert steps[0].agent_role == AgentRole.researcher
        assert steps[1].agent_role == AgentRole.coder

    @pytest.mark.asyncio
    async def test_json_array_of_strings(self, parser):
        raw = json.dumps(["Step one", "Step two", "Step three"])
        steps = await parser.parse(raw)
        assert len(steps) == 3
        assert steps[0].description == "Step one"

    @pytest.mark.asyncio
    async def test_json_with_dependencies(self, parser):
        step1_id = "step-1"
        raw = json.dumps([
            {"id": step1_id, "description": "First"},
            {"description": "Second", "depends_on": [step1_id]},
        ])
        steps = await parser.parse(raw)
        assert len(steps) == 2
        assert steps[1].depends_on == [step1_id]

    @pytest.mark.asyncio
    async def test_json_with_complexity(self, parser):
        raw = json.dumps([
            {"description": "Easy task", "complexity": "light"},
            {"description": "Hard task", "complexity": "heavy"},
        ])
        steps = await parser.parse(raw)
        assert steps[0].complexity == TaskComplexity.light
        assert steps[1].complexity == TaskComplexity.heavy



class TestMarkdownParsing:
    """Test markdown list parsing."""

    @pytest.mark.asyncio
    async def test_unordered_list(self, parser):
        raw = "- Research best practices\n- Implement the solution\n- Write tests"
        steps = await parser.parse(raw)
        assert len(steps) == 3
        assert "Research" in steps[0].description

    @pytest.mark.asyncio
    async def test_ordered_list(self, parser):
        raw = "1. Plan the architecture\n2. Code the backend\n3. Deploy to production"
        steps = await parser.parse(raw)
        assert len(steps) == 3
        assert "Plan" in steps[0].description

    @pytest.mark.asyncio
    async def test_infers_sequential_dependencies(self, parser):
        raw = "- Step A\n- Step B\n- Step C"
        steps = await parser.parse(raw)
        # Step B depends on Step A, Step C depends on Step B
        assert steps[1].depends_on == [steps[0].id]
        assert steps[2].depends_on == [steps[1].id]

    @pytest.mark.asyncio
    async def test_single_item_not_parsed_as_list(self, parser):
        raw = "- Just one item"
        # Single item shouldn't trigger markdown parser (needs >= 2)
        steps = await parser.parse(raw)
        assert len(steps) >= 1


class TestRoleInference:
    """Test automatic role inference from keywords."""

    @pytest.mark.asyncio
    async def test_research_keywords(self, parser):
        raw = "- Research the best framework\n- Implement the solution"
        steps = await parser.parse(raw)
        assert steps[0].agent_role == AgentRole.researcher

    @pytest.mark.asyncio
    async def test_code_keywords(self, parser):
        raw = "- Write the API endpoint\n- Test it works"
        steps = await parser.parse(raw)
        assert steps[0].agent_role == AgentRole.coder

    @pytest.mark.asyncio
    async def test_executor_keywords(self, parser):
        raw = "- Run the test suite\n- Check output"
        steps = await parser.parse(raw)
        assert steps[0].agent_role == AgentRole.executor


class TestEdgeCases:
    """Test edge cases."""

    @pytest.mark.asyncio
    async def test_empty_input(self, parser):
        steps = await parser.parse("")
        assert steps == []

    @pytest.mark.asyncio
    async def test_whitespace_only(self, parser):
        steps = await parser.parse("   \n\n  ")
        assert steps == []

    @pytest.mark.asyncio
    async def test_invalid_json(self, parser):
        raw = "{not valid json at all"
        # Should fall through to LLM or sentence split
        steps = await parser.parse(raw)
        assert len(steps) >= 1  # Sentence split fallback
