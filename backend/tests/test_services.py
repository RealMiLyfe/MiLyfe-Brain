"""MiLyfe Brain — Service Layer Tests."""

import pytest


class TestTopicDetector:
    """Test input topic classification."""

    def test_slash_command(self):
        from services.topic_detector import detect_topic
        from models.schemas import TopicType
        topic, _ = detect_topic("/review code")
        assert topic == TopicType.COMMAND

    def test_question_mark(self):
        from services.topic_detector import detect_topic
        from models.schemas import TopicType
        topic, _ = detect_topic("how does this work?")
        assert topic == TopicType.QUESTION

    def test_edit_request(self):
        from services.topic_detector import detect_topic
        from models.schemas import TopicType
        topic, _ = detect_topic("change the color to red")
        assert topic == TopicType.EDIT

    def test_new_task(self):
        from services.topic_detector import detect_topic
        from models.schemas import TopicType
        topic, _ = detect_topic("Build a weather dashboard with charts and graphs")
        assert topic == TopicType.NEW_TASK

    def test_feedback_positive(self):
        from services.topic_detector import detect_topic
        from models.schemas import TopicType
        topic, _ = detect_topic("Great job, thanks!")
        assert topic == TopicType.FEEDBACK


class TestAgentLearning:
    """Test agent learning service."""

    def test_record_correction(self):
        from services.agent_learning import agent_learning
        from models.schemas import AgentRole
        cid = agent_learning.record_correction(
            agent_role=AgentRole.CODER,
            original_output="def foo(): pass",
            correction="Always add type hints to functions",
            context="writing python functions",
        )
        assert cid

    def test_correction_retrieval(self):
        from services.agent_learning import agent_learning
        from models.schemas import AgentRole
        agent_learning.record_correction(
            agent_role=AgentRole.CODER,
            original_output="x = 1",
            correction="Use constants for magic numbers",
            context="python variables",
        )
        prompt = agent_learning.get_corrections_for_prompt(AgentRole.CODER, "python variables")
        assert "constants" in prompt or "corrections" in prompt.lower()

    def test_failure_pattern_tracking(self):
        from services.agent_learning import agent_learning
        from models.schemas import AgentRole
        # Record same error multiple times
        for _ in range(3):
            agent_learning.record_failure(
                agent_role=AgentRole.EXECUTOR,
                error_message="FileNotFoundError: /workspace/missing.txt",
                task_context="file operations",
            )
        prevention = agent_learning.get_failure_prevention_prompt(AgentRole.EXECUTOR)
        assert "FileNotFoundError" in prevention or "failure" in prevention.lower()

    def test_specialization_tracking(self):
        from services.agent_learning import agent_learning
        from models.schemas import AgentRole
        # Record successes in a domain
        for _ in range(5):
            agent_learning.record_success(AgentRole.CODER, "python api endpoint fastapi")
        report = agent_learning.get_performance_report()
        assert AgentRole.CODER.value in report

    def test_domain_detection(self):
        from services.agent_learning import agent_learning
        assert agent_learning._detect_domain("create a REST API endpoint") == "api"
        assert agent_learning._detect_domain("write pytest unit tests") == "testing"
        assert agent_learning._detect_domain("deploy with docker container") == "devops"
        assert agent_learning._detect_domain("random gibberish") == "general"


class TestWebhooks:
    """Test webhook service."""

    def test_register_outgoing(self):
        from services.webhooks import webhook_service
        hook_id = webhook_service.register_outgoing(
            name="test_hook",
            url="http://example.com/webhook",
            events=["playbook.completed"],
        )
        assert hook_id
        hooks = webhook_service.list_outgoing()
        assert any(h["id"] == hook_id for h in hooks)

    def test_register_incoming(self):
        from services.webhooks import webhook_service
        result = webhook_service.register_incoming(
            name="github_push",
            action="notify",
            action_config={"title": "Push received"},
        )
        assert "id" in result
        assert "token" in result
        assert "url" in result

    def test_condition_matching(self):
        from services.webhooks import webhook_service
        # Equality
        assert webhook_service._matches_condition({"status": "completed"}, {"status": "completed"})
        assert not webhook_service._matches_condition({"status": "completed"}, {"status": "failed"})
        # Contains
        assert webhook_service._matches_condition(
            {"message": "contains:error"},
            {"message": "there was an error in the build"},
        )
        # Empty condition = always match
        assert webhook_service._matches_condition({}, {"anything": "goes"})

    def test_trigger_registration(self):
        from services.webhooks import webhook_service
        rule_id = webhook_service.register_trigger(
            name="test_rule",
            source="git",
            condition={"git_event": "push"},
            action="notify",
        )
        assert rule_id
        triggers = webhook_service.list_triggers()
        assert any(t["id"] == rule_id for t in triggers)


class TestPlaybookVariables:
    """Test playbook variable system."""

    def test_basic_resolution(self):
        from graphs.playbook_engine import PlaybookVariables
        pv = PlaybookVariables({"name": "Brain", "version": "1.0"})
        assert pv.resolve("Hello {{name}} v{{version}}") == "Hello Brain v1.0"

    def test_step_result_resolution(self):
        from graphs.playbook_engine import PlaybookVariables
        pv = PlaybookVariables()
        pv.set_step_result("step_1", "API built successfully")
        result = pv.resolve("Previous result: {{step_1.result}}")
        assert "API built successfully" in result

    def test_unresolved_stays(self):
        from graphs.playbook_engine import PlaybookVariables
        pv = PlaybookVariables()
        result = pv.resolve("Value: {{undefined_var}}")
        assert "{{undefined_var}}" in result

    def test_env_resolution(self):
        import os
        from graphs.playbook_engine import PlaybookVariables
        os.environ["TEST_MILYFE_VAR"] = "test_value"
        pv = PlaybookVariables()
        result = pv.resolve("Env: {{env.TEST_MILYFE_VAR}}")
        assert "test_value" in result
        del os.environ["TEST_MILYFE_VAR"]


class TestStepConditions:
    """Test playbook conditional execution."""

    def test_always(self):
        from graphs.playbook_engine import StepCondition, PlaybookVariables
        assert StepCondition("always").evaluate(PlaybookVariables())

    def test_never(self):
        from graphs.playbook_engine import StepCondition, PlaybookVariables
        assert not StepCondition("never").evaluate(PlaybookVariables())

    def test_contains(self):
        from graphs.playbook_engine import StepCondition, PlaybookVariables
        pv = PlaybookVariables()
        pv.set_step_result("step_1", "there was an error in the output")
        cond = StepCondition("{{step_1.result}} contains 'error'")
        assert cond.evaluate(pv)

    def test_not_empty(self):
        from graphs.playbook_engine import StepCondition, PlaybookVariables
        pv = PlaybookVariables({"result": "something"})
        assert StepCondition("{{result}} not empty").evaluate(pv)

    def test_equality(self):
        from graphs.playbook_engine import StepCondition, PlaybookVariables
        pv = PlaybookVariables({"status": "ready"})
        assert StepCondition("{{status}} == 'ready'").evaluate(pv)
        assert not StepCondition("{{status}} == 'blocked'").evaluate(pv)

    def test_inequality(self):
        from graphs.playbook_engine import StepCondition, PlaybookVariables
        pv = PlaybookVariables({"mode": "production"})
        assert StepCondition("{{mode}} != 'test'").evaluate(pv)


class TestProjectIntelligence:
    """Test project type detection."""

    def test_domain_keywords(self):
        from services.project_intelligence import project_intelligence
        # Should detect without crashing
        model = project_intelligence.get_mental_model()
        assert "project_type" in model

    def test_file_lock(self):
        from services.project_intelligence import project_intelligence
        assert project_intelligence.acquire_file_lock("test.py", "agent_1")
        assert not project_intelligence.acquire_file_lock("test.py", "agent_2")
        project_intelligence.release_file_lock("test.py", "agent_1")
        assert project_intelligence.acquire_file_lock("test.py", "agent_2")
        project_intelligence.release_file_lock("test.py", "agent_2")

    def test_impact_analysis(self):
        from services.project_intelligence import project_intelligence
        result = project_intelligence.get_impact_analysis("nonexistent.py")
        assert "risk_level" in result
        assert result["risk_level"] == "low"
