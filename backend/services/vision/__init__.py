"""
MiLyfe Brain Vision Features.

Future-forward capabilities for the MiLyfe Brain platform:
- User Intent Engine (clarify ambiguity before executing)
- Execution Replay / Time Travel (timeline scrubber, undo)
- Self-improving Prompts (A/B testing, auto few-shot)
- Code Graph (AST-level function relationships)
- Integrations (Jira, Linear, Slack, Discord, Calendar)
- Distributed Task Queue (RabbitMQ/SQS)
- Agent Pooling (pre-warm instances)
- Brain-to-Brain Communication
- Dream Mode (overnight autonomous processing)
- IoT Integration, AR/VR Workspace, Intelligence OS
"""

from .intent_engine import IntentEngine, intent_engine
from .execution_replay import ExecutionReplayService, replay_service
from .self_improving_prompts import SelfImprovingPrompts, prompt_optimizer
from .code_graph import CodeGraphService, code_graph
from .integrations import IntegrationHub, integration_hub
from .distributed_queue import DistributedTaskQueue, distributed_queue
from .agent_pool import AgentPool, agent_pool
from .brain_communication import BrainNetwork, brain_network
from .dream_mode import DreamModeService, dream_service
from .advanced_systems import IoTBridge, ARVRWorkspace, IntelligenceOS

__all__ = [
    "IntentEngine", "intent_engine",
    "ExecutionReplayService", "replay_service",
    "SelfImprovingPrompts", "prompt_optimizer",
    "CodeGraphService", "code_graph",
    "IntegrationHub", "integration_hub",
    "DistributedTaskQueue", "distributed_queue",
    "AgentPool", "agent_pool",
    "BrainNetwork", "brain_network",
    "DreamModeService", "dream_service",
    "IoTBridge", "ARVRWorkspace", "IntelligenceOS",
]
