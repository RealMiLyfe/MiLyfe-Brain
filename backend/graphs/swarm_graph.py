"""Swarm graph — Sub-swarm execution patterns.

Provides reusable execution patterns for multi-agent collaboration:
- parallel_execution: Run tasks across agents simultaneously
- sequential_execution: Run tasks one after another with a single agent
- debate_execution: Multiple agents debate, best answer wins
"""

from __future__ import annotations

import asyncio
import logging
from typing import List

from agents.base import BaseAgent
from agents.factory import get_agent_factory

logger = logging.getLogger(__name__)


async def parallel_execution(tasks: List[str], agents: List[BaseAgent]) -> List[str]:
    """Execute tasks in parallel using provided agents.

    Each task is assigned to the corresponding agent by index.
    If there are more tasks than agents, agents are reused round-robin.

    Args:
        tasks: List of task descriptions to execute.
        agents: List of agent instances to use.

    Returns:
        List of result strings in the same order as tasks.
    """
    if not tasks:
        return []

    if not agents:
        raise ValueError("No agents provided for parallel execution")

    async def _run(task: str, agent: BaseAgent) -> str:
        try:
            return await agent.think(task)
        except Exception as e:
            logger.error("Parallel task failed: %s", e)
            return f"Error: {e}"

    # Map tasks to agents round-robin
    coros = [
        _run(task, agents[i % len(agents)])
        for i, task in enumerate(tasks)
    ]

    results = await asyncio.gather(*coros)
    return list(results)


async def sequential_execution(tasks: List[str], agent: BaseAgent) -> List[str]:
    """Execute tasks sequentially using a single agent.

    Each task is executed one after another. The agent retains context
    from previous tasks through its thought history.

    Args:
        tasks: List of task descriptions to execute in order.
        agent: The agent instance to use for all tasks.

    Returns:
        List of result strings in task order.
    """
    results: List[str] = []

    for task in tasks:
        try:
            result = await agent.think(task)
            results.append(result)
        except Exception as e:
            logger.error("Sequential task failed: %s", e)
            results.append(f"Error: {e}")

    return results


async def debate_execution(task: str, agents: List[BaseAgent]) -> str:
    """Multiple agents debate a task, best answer wins.

    Process:
    1. All agents independently produce an answer
    2. Each agent sees all other answers and produces a critique
    3. Agents vote on which answer is best (including their own revised answer)
    4. The most-voted answer wins

    Args:
        task: The task/question to debate.
        agents: List of agents (at least 2) to participate.

    Returns:
        The winning answer string.
    """
    if len(agents) < 2:
        if agents:
            return await agents[0].think(task)
        raise ValueError("At least 2 agents required for debate")

    # Round 1: Independent answers
    logger.info("Debate round 1: %d agents producing independent answers", len(agents))
    initial_coros = [agent.think(task) for agent in agents]
    initial_answers = await asyncio.gather(*initial_coros, return_exceptions=True)

    answers: List[str] = []
    for ans in initial_answers:
        if isinstance(ans, Exception):
            answers.append(f"[Agent failed: {ans}]")
        else:
            answers.append(ans)

    # Round 2: Critique and revision
    logger.info("Debate round 2: agents critiquing and revising")
    revision_prompt_template = (
        f"Original task: {task}\n\n"
        "Here are all the proposed answers:\n\n"
        "{all_answers}\n\n"
        "Please critique these answers and provide your FINAL best answer. "
        "Consider the strengths and weaknesses of each approach."
    )

    all_answers_text = "\n\n".join(
        f"--- Answer {i+1} ---\n{ans}" for i, ans in enumerate(answers)
    )

    revision_coros = [
        agent.think(
            revision_prompt_template.format(all_answers=all_answers_text)
        )
        for agent in agents
    ]
    revised_answers = await asyncio.gather(*revision_coros, return_exceptions=True)

    final_answers: List[str] = []
    for ans in revised_answers:
        if isinstance(ans, Exception):
            final_answers.append("")
        else:
            final_answers.append(ans)

    # Round 3: Vote for the best
    logger.info("Debate round 3: voting")
    vote_prompt = (
        f"Original task: {task}\n\n"
        "Final answers from all participants:\n\n"
        "{all_final}\n\n"
        "Vote for the BEST answer by responding with ONLY the number (1, 2, 3, etc.)."
    )

    all_final_text = "\n\n".join(
        f"--- Final Answer {i+1} ---\n{ans}" for i, ans in enumerate(final_answers) if ans
    )

    # Use first agent to be the judge (could also use a separate judge agent)
    try:
        vote_result = await agents[0].think(
            vote_prompt.format(all_final=all_final_text)
        )
        # Try to extract the vote number
        import re
        numbers = re.findall(r"\d+", vote_result)
        if numbers:
            winner_idx = int(numbers[0]) - 1
            if 0 <= winner_idx < len(final_answers) and final_answers[winner_idx]:
                return final_answers[winner_idx]
    except Exception as e:
        logger.warning("Vote failed: %s, returning longest answer", e)

    # Fallback: return the longest answer (heuristic for most thorough)
    valid_answers = [a for a in final_answers if a]
    if valid_answers:
        return max(valid_answers, key=len)

    # Ultimate fallback
    return answers[0] if answers else "Debate produced no result."
