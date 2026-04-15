"""
Workflow Execution Engine
Processes conversations through workflow nodes, managing state transitions and variable extraction.
"""

import re
import json
import httpx
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.models import (
    Workflow, WorkflowNode, WorkflowEdge, Conversation, ConversationMessage, Agent
)


class WorkflowEngine:
    """Executes workflow nodes and manages conversation state."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def process_message(
        self,
        conversation_id: str,
        user_message: str,
    ) -> Dict[str, Any]:
        """
        Process a user message through the current workflow node.
        Returns the agent's response and any state changes.
        """
        # Load conversation
        result = await self.db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            return {"error": "Conversation not found"}

        # Load agent
        agent_result = await self.db.execute(
            select(Agent).where(Agent.id == conversation.agent_id)
        )
        agent = agent_result.scalar_one_or_none()

        if not agent or not agent.active_workflow_id:
            return await self._llm_response(agent, conversation, user_message)

        # Load workflow with nodes and edges
        wf_result = await self.db.execute(
            select(Workflow)
            .options(selectinload(Workflow.nodes), selectinload(Workflow.edges))
            .where(Workflow.id == agent.active_workflow_id)
        )
        workflow = wf_result.scalar_one_or_none()
        if not workflow:
            return await self._llm_response(agent, conversation, user_message)

        # Get current node
        current_node = None
        if conversation.current_node_id:
            for node in workflow.nodes:
                if node.id == conversation.current_node_id:
                    current_node = node
                    break

        if not current_node:
            return {"error": "Current node not found in workflow"}

        # Process based on node type
        response = await self._execute_node(
            current_node, conversation, workflow, agent, user_message
        )

        # Save conversation state
        await self.db.flush()

        return response

    async def _execute_node(
        self,
        node: WorkflowNode,
        conversation: Conversation,
        workflow: Workflow,
        agent: Agent,
        user_message: str,
    ) -> Dict[str, Any]:
        """Execute a specific workflow node."""

        node_type = node.node_type.value if hasattr(node.node_type, 'value') else node.node_type
        config = node.config or {}

        handlers = {
            "start": self._handle_start,
            "end": self._handle_end,
            "ai_prompt": self._handle_ai_prompt,
            "question": self._handle_question,
            "condition": self._handle_condition,
            "transfer": self._handle_transfer,
            "webhook": self._handle_webhook,
            "knowledge_lookup": self._handle_knowledge_lookup,
            "set_variable": self._handle_set_variable,
            "wait": self._handle_wait,
            "collect_input": self._handle_collect_input,
            "api_call": self._handle_api_call,
            "function_call": self._handle_function_call,
        }

        handler = handlers.get(node_type)
        if not handler:
            return {"error": f"Unknown node type: {node_type}"}

        return await handler(node, conversation, workflow, agent, user_message)

    async def _handle_start(self, node, conversation, workflow, agent, user_message):
        """Move to the next node from start."""
        next_node = await self._get_next_node(node, workflow, conversation)
        if next_node:
            conversation.current_node_id = next_node.id
            return await self._execute_node(next_node, conversation, workflow, agent, user_message)
        return {"response": "Workflow started", "node_type": "start"}

    async def _handle_end(self, node, conversation, workflow, agent, user_message):
        """End the conversation."""
        conversation.status = "completed"
        end_msg = agent.end_call_message or "Görüşmemiz sona erdi. Teşekkür ederim!"
        return {
            "response": end_msg,
            "node_type": "end",
            "conversation_ended": True,
        }

    async def _handle_ai_prompt(self, node, conversation, workflow, agent, user_message):
        """Process through LLM with the configured prompt."""
        config = node.config or {}
        prompt_template = config.get("prompt", "")

        # Interpolate variables
        prompt = self._interpolate_variables(prompt_template, conversation.variables)

        # Save user response to variable if configured
        save_to = config.get("save_response_to")
        if save_to and user_message:
            variables = conversation.variables or {}
            variables[save_to] = user_message
            conversation.variables = variables

        # TODO: Call actual LLM here
        # For now, return the interpolated prompt as the agent's message
        response_text = prompt

        # Advance to next node
        next_node = await self._get_next_node(node, workflow, conversation)
        if next_node:
            conversation.current_node_id = next_node.id

        return {
            "response": response_text,
            "node_type": "ai_prompt",
            "next_node_id": next_node.id if next_node else None,
            "variables_updated": {save_to: user_message} if save_to else {},
        }

    async def _handle_question(self, node, conversation, workflow, agent, user_message):
        """Ask a question and validate/save the response."""
        config = node.config or {}
        save_to = config.get("save_to_variable")
        expected_type = config.get("expected_type", "text")
        choices = config.get("choices", [])
        max_retries = config.get("max_retries", 3)

        # If this is the first time at this node (no user message yet), ask the question
        retry_key = f"_retry_{node.id}"
        retries = (conversation.variables or {}).get(retry_key, 0)

        if user_message:
            # Validate response
            valid = True
            processed_value = user_message

            if expected_type == "number":
                try:
                    processed_value = float(user_message.replace(",", "."))
                except ValueError:
                    valid = False

            elif expected_type == "yes_no":
                lower = user_message.lower().strip()
                if lower in ["evet", "yes", "e", "doğru", "true"]:
                    processed_value = "yes"
                elif lower in ["hayır", "no", "h", "yanlış", "false"]:
                    processed_value = "no"
                else:
                    valid = False

            elif expected_type == "choice" and choices:
                # Fuzzy match against choices
                matched = None
                for choice in choices:
                    if choice.lower() in user_message.lower() or user_message.lower() in choice.lower():
                        matched = choice
                        break
                if matched:
                    processed_value = matched
                else:
                    valid = False

            if valid:
                # Save to variable
                if save_to:
                    variables = conversation.variables or {}
                    variables[save_to] = processed_value
                    variables.pop(retry_key, None)
                    conversation.variables = variables

                # Advance to next node
                next_node = await self._get_next_node(node, workflow, conversation)
                if next_node:
                    conversation.current_node_id = next_node.id
                    # If next node is also a question, return its question text
                    if next_node.node_type.value == "question":
                        return {
                            "response": next_node.config.get("question_text", ""),
                            "node_type": "question",
                            "choices": next_node.config.get("choices", []),
                        }
                    return await self._execute_node(next_node, conversation, workflow, agent, "")

                return {
                    "response": "Teşekkürler!",
                    "node_type": "question",
                    "variables_updated": {save_to: processed_value},
                }
            else:
                # Retry
                variables = conversation.variables or {}
                variables[retry_key] = retries + 1
                conversation.variables = variables

                if retries >= max_retries:
                    next_node = await self._get_next_node(node, workflow, conversation)
                    if next_node:
                        conversation.current_node_id = next_node.id
                    return {
                        "response": "Devam edelim.",
                        "node_type": "question",
                    }

                retry_prompt = config.get("retry_prompt", "Anlayamadım, tekrar eder misiniz?")
                if expected_type == "choice" and choices:
                    retry_prompt += f" Seçenekler: {', '.join(choices)}"
                return {
                    "response": retry_prompt,
                    "node_type": "question",
                    "retry": True,
                }

        # First visit — ask the question
        question_text = config.get("question_text", "")
        return {
            "response": question_text,
            "node_type": "question",
            "choices": choices if expected_type == "choice" else [],
        }

    async def _handle_condition(self, node, conversation, workflow, agent, user_message):
        """Evaluate conditions and branch."""
        config = node.config or {}
        conditions = config.get("conditions", [])
        variables = conversation.variables or {}

        matched_next = None
        for cond in conditions:
            var_name = cond.get("variable", "")
            operator = cond.get("operator", "equals")
            expected = cond.get("value", "")
            var_value = str(variables.get(var_name, ""))

            if self._evaluate_condition(var_value, operator, expected):
                next_id = cond.get("next_node")
                if next_id:
                    for n in workflow.nodes:
                        if n.id == next_id:
                            matched_next = n
                            break
                break

        if not matched_next:
            # Check for edges with matching conditions
            for edge in workflow.edges:
                if edge.source_node_id == node.id:
                    if edge.condition:
                        var_name = edge.condition.get("variable", "")
                        operator = edge.condition.get("operator", "equals")
                        expected = edge.condition.get("value", "")
                        var_value = str(variables.get(var_name, ""))
                        if self._evaluate_condition(var_value, operator, expected):
                            for n in workflow.nodes:
                                if n.id == edge.target_node_id:
                                    matched_next = n
                                    break
                            break
                    elif edge.edge_type == "fallback":
                        for n in workflow.nodes:
                            if n.id == edge.target_node_id:
                                matched_next = n
                                break

        if not matched_next:
            # Default: get any next node
            matched_next = await self._get_next_node(node, workflow, conversation)

        if matched_next:
            conversation.current_node_id = matched_next.id
            return await self._execute_node(matched_next, conversation, workflow, agent, user_message)

        return {"response": "Bir hata oluştu.", "node_type": "condition"}

    async def _handle_transfer(self, node, conversation, workflow, agent, user_message):
        config = node.config or {}
        return {
            "response": config.get("transfer_message", "Sizi bir uzmanımıza bağlıyorum."),
            "node_type": "transfer",
            "transfer_to": config.get("transfer_to", "human_agent"),
            "department": config.get("department", ""),
            "priority": config.get("priority", "normal"),
        }

    async def _handle_webhook(self, node, conversation, workflow, agent, user_message):
        config = node.config or {}
        url = config.get("url", "")
        method = config.get("method", "POST")
        headers = config.get("headers", {})
        body_template = config.get("body_template", {})
        timeout = config.get("timeout", 5)
        save_to = config.get("save_response_to")

        # Interpolate body
        body = {}
        for key, val in body_template.items():
            body[key] = self._interpolate_variables(str(val), conversation.variables)

        try:
            async with httpx.AsyncClient() as client:
                if method.upper() == "POST":
                    resp = await client.post(url, json=body, headers=headers, timeout=timeout)
                else:
                    resp = await client.get(url, headers=headers, timeout=timeout)

                result_data = resp.text
                try:
                    result_data = resp.json()
                except:
                    pass

                if save_to:
                    variables = conversation.variables or {}
                    variables[save_to] = result_data
                    conversation.variables = variables

        except Exception as e:
            result_data = {"error": str(e)}

        next_node = await self._get_next_node(node, workflow, conversation)
        if next_node:
            conversation.current_node_id = next_node.id

        return {
            "response": "",
            "node_type": "webhook",
            "webhook_result": result_data,
        }

    async def _handle_knowledge_lookup(self, node, conversation, workflow, agent, user_message):
        config = node.config or {}
        query_var = config.get("query_variable", "")
        query = (conversation.variables or {}).get(query_var, user_message)
        save_to = config.get("save_to_variable", "answer")

        # TODO: Implement actual knowledge base search
        variables = conversation.variables or {}
        variables[save_to] = f"[Knowledge result for: {query}]"
        conversation.variables = variables

        next_node = await self._get_next_node(node, workflow, conversation)
        if next_node:
            conversation.current_node_id = next_node.id
            return await self._execute_node(next_node, conversation, workflow, agent, user_message)

        return {"response": "", "node_type": "knowledge_lookup"}

    async def _handle_set_variable(self, node, conversation, workflow, agent, user_message):
        config = node.config or {}
        var_name = config.get("variable", "")
        value_type = config.get("value_type", "static")
        value = config.get("value", "")

        variables = conversation.variables or {}

        if value_type == "static":
            variables[var_name] = value
        elif value_type == "from_variable":
            variables[var_name] = variables.get(value, "")
        elif value_type == "expression":
            variables[var_name] = self._interpolate_variables(value, variables)

        conversation.variables = variables

        next_node = await self._get_next_node(node, workflow, conversation)
        if next_node:
            conversation.current_node_id = next_node.id
            return await self._execute_node(next_node, conversation, workflow, agent, user_message)

        return {"response": "", "node_type": "set_variable"}

    async def _handle_wait(self, node, conversation, workflow, agent, user_message):
        config = node.config or {}
        message = config.get("message", "Bir saniye lütfen...")

        next_node = await self._get_next_node(node, workflow, conversation)
        if next_node:
            conversation.current_node_id = next_node.id

        return {
            "response": message,
            "node_type": "wait",
            "duration_seconds": config.get("duration_seconds", 2),
        }

    async def _handle_collect_input(self, node, conversation, workflow, agent, user_message):
        config = node.config or {}
        input_type = config.get("input_type", "free_text")
        save_to = config.get("save_to_variable", "")
        validation_regex = config.get("validation_regex", "")

        if user_message:
            valid = True
            if validation_regex:
                if not re.match(validation_regex, user_message):
                    valid = False

            if valid:
                if save_to:
                    variables = conversation.variables or {}
                    variables[save_to] = user_message
                    conversation.variables = variables

                next_node = await self._get_next_node(node, workflow, conversation)
                if next_node:
                    conversation.current_node_id = next_node.id
                    return await self._execute_node(next_node, conversation, workflow, agent, "")

                return {"response": "Teşekkürler!", "node_type": "collect_input"}
            else:
                error_msg = config.get("error_message", "Geçersiz giriş, lütfen tekrar deneyin.")
                return {"response": error_msg, "node_type": "collect_input", "retry": True}

        prompt = config.get("prompt", "Lütfen bilgi girin.")
        return {"response": prompt, "node_type": "collect_input"}

    async def _handle_api_call(self, node, conversation, workflow, agent, user_message):
        config = node.config or {}
        # Similar to webhook but with auth support
        next_node = await self._get_next_node(node, workflow, conversation)
        if next_node:
            conversation.current_node_id = next_node.id
        return {"response": "", "node_type": "api_call"}

    async def _handle_function_call(self, node, conversation, workflow, agent, user_message):
        config = node.config or {}
        next_node = await self._get_next_node(node, workflow, conversation)
        if next_node:
            conversation.current_node_id = next_node.id
        return {"response": "", "node_type": "function_call"}

    # ─── Helpers ──────────────────────────────────────────────────────

    async def _get_next_node(
        self, current_node: WorkflowNode, workflow: Workflow, conversation: Conversation
    ) -> Optional[WorkflowNode]:
        """Find the next node by following edges."""
        for edge in workflow.edges:
            if edge.source_node_id == current_node.id:
                # Check condition if any
                if edge.condition:
                    var_name = edge.condition.get("variable", "")
                    operator = edge.condition.get("operator", "equals")
                    expected = edge.condition.get("value", "")
                    var_value = str((conversation.variables or {}).get(var_name, ""))
                    if not self._evaluate_condition(var_value, operator, expected):
                        continue

                for node in workflow.nodes:
                    if node.id == edge.target_node_id:
                        return node
        return None

    def _evaluate_condition(self, value: str, operator: str, expected: str) -> bool:
        """Evaluate a condition."""
        value = value.lower().strip()
        expected = expected.lower().strip()

        if operator == "equals":
            return value == expected
        elif operator == "not_equals":
            return value != expected
        elif operator == "contains":
            return expected in value
        elif operator == "greater_than":
            try:
                return float(value) > float(expected)
            except ValueError:
                return False
        elif operator == "less_than":
            try:
                return float(value) < float(expected)
            except ValueError:
                return False
        elif operator == "is_empty":
            return not value
        elif operator == "is_not_empty":
            return bool(value)
        elif operator == "matches_regex":
            return bool(re.match(expected, value))
        return False

    def _interpolate_variables(self, template: str, variables: Dict[str, Any]) -> str:
        """Replace {{variable}} placeholders with actual values."""
        if not variables:
            return template

        def replacer(match):
            var_name = match.group(1).strip()
            return str(variables.get(var_name, match.group(0)))

        return re.sub(r'\{\{(\w+)\}\}', replacer, template)

    async def _llm_response(
        self, agent: Optional[Agent], conversation: Conversation, user_message: str
    ) -> Dict[str, Any]:
        """Fallback: direct LLM response without workflow."""
        # TODO: Integrate with actual LLM provider
        return {
            "response": f"[LLM response to: {user_message}]",
            "node_type": "free_conversation",
        }
