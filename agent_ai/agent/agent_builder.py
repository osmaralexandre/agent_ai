from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain.schema import HumanMessage, SystemMessage
from langchain_community.callbacks import get_openai_callback
from langchain_openai import ChatOpenAI

from agent_ai.memory.memory_manager import MemoryProvider
from agent_ai.utils.read_files import FileUtils


# =============================================================================
# Agent
# =============================================================================
class Agent:
    """
    LLM agent responsible for building prompts, injecting memory/context, and
    executing model calls.

    Parameters
    ----------
    name : str
        Name of the agent.
    config : dict
        Configuration dictionary containing model settings, prompt name, etc.
    prompt_dir : Path
        Directory containing the base system prompt files.
    short_term_memory_provider : MemoryProvider, optional
        Memory provider instance for retrieving short-term memory context.
    long_term_memory_provider : MemoryProvider, optional
        Memory provider instance for retrieving long-term memory context.
    context_text : str, optional
        Optional static context that is appended to the prompt.

    Attributes
    ----------
    name : str
        Agent name.
    system_prompt : str
        Base system prompt loaded from file.
    use_context : bool
        Whether static context should be included.
    use_memory_history : bool
        Whether conversation memory should be included.
    """

    def __init__(
        self,
        name: str,
        config: Dict[str, Any],
        prompt_dir: Path,
        short_term_memory_provider: Optional[MemoryProvider] = None,
        long_term_memory_provider: Optional[MemoryProvider] = None,
        context_text: Optional[str] = None,
    ):
        self.name = name
        self.config = config
        self.model = config["model"]
        self.enabled = config["enabled"]
        self.prompt_name = config["prompt_name"]
        self.temperature = config["temperature"]
        self.use_context = config["use_context"]
        self.use_memory_history = config["use_memory_history"]
        self.short_term_memory_provider = short_term_memory_provider
        self.long_term_memory_provider = long_term_memory_provider
        self.context_text = context_text
        # Load system prompt
        self.system_prompt = FileUtils.read_text(
            prompt_dir / f"{self.prompt_name}.txt"
        ).strip()

    # -------------------------------------------------------------------------
    #  Context formatting
    # -------------------------------------------------------------------------
    def _format_context_as_text(self) -> str:
        """
        Return formatted static context if enabled.

        Returns
        -------
        str
            Context text, or empty string if disabled.
        """

        if not self.use_context or not self.context_text:
            return ""

        return self.context_text.strip()

    # -------------------------------------------------------------------------
    #  Short Term Memory formatting
    # -------------------------------------------------------------------------
    def _format_short_term_memory_as_text(self) -> str:
        """
        Build a formatted text representation of short-term memory.

        Returns
        -------
        str
            Short-term memory block formatted as plain text, or empty string if disabled.
        """

        if not self.use_memory_history or not self.short_term_memory_provider:
            return ""

        history = self.short_term_memory_provider.get_messages(
            agent_name=self.name,
        )

        if not history:
            return ""

        lines = ["Histórico da conversa (não continuar, apenas referência):"]
        for item in history:
            role = "Usuário" if item["role"] == "user" else "Assistente"
            lines.append(f"{role}: {item['content']}")

        return "\n".join(lines)

    # -------------------------------------------------------------------------
    #  Long Term Memory formatting
    # -------------------------------------------------------------------------
    def _format_long_term_memory_as_text(self, user_input: str) -> str:
        """
        Build a formatted text representation of long-term memory.

        Returns
        -------
        str
            Long-term memory block formatted as plain text, or empty string if disabled.
        """

        if not self.use_memory_history or not self.long_term_memory_provider:
            return ""

        history = self.long_term_memory_provider.get_messages(
            query=user_input,
            top_n=3,
        )

        if not history:
            return ""

        lines = ["Histórico da conversa (não continuar, apenas referência):"]
        for item in history:
            role = "Usuário" if item["role"] == "user" else "Assistente"
            lines.append(f"{role}: {item['message']}")

        return "\n".join(lines)

    # -------------------------------------------------------------------------
    #  Message Builder
    # -------------------------------------------------------------------------
    def _build_messages(self, user_input: str) -> List[Any]:
        """
        Build the complete message list to be sent to the LLM.

        Parameters
        ----------
        user_input : str
            Raw user message.

        Returns
        -------
        list
            List of SystemMessage and HumanMessage objects ready for model call.
        """

        context_text = self._format_context_as_text()
        short_term_memory_text = self._format_short_term_memory_as_text()
        long_term_memory_text = self._format_long_term_memory_as_text(
            user_input
        )

        # Monta as seções do system_prompt
        system_sections = [self.system_prompt]

        if short_term_memory_text:
            system_sections.append(
                f"=== MEMÓRIA DE CURTO PRAZO ===\n{short_term_memory_text}"
            )

        if long_term_memory_text:
            system_sections.append(
                f"=== MEMÓRIA DE LONGO PRAZO ===\n{long_term_memory_text}"
            )

        if context_text:
            system_sections.append(f"=== CONTEXTO ===\n{context_text}")

        system_content = "\n\n".join(system_sections)

        messages = [
            SystemMessage(content=system_content),
            HumanMessage(content=user_input),
        ]

        return messages

        # ---------------------------------------------------------------------

    #  Agente Execution
    # -------------------------------------------------------------------------
    def run(self, message: str) -> Dict[str, Any]:
        """
        Execute the LLM agent with the given message.

        Parameters
        ----------
        message : str
            User input message.

        Returns
        -------
        dict
            Response dictionary with model output and token usage.

        Notes
        -----
        Returns a raw echo if the agent is disabled.
        """

        if not self.enabled:
            return {
                "response": message,
                "tokens_prompt": 0,
                "tokens_completion": 0,
                "tokens_total": 0,
                "cost_usd": 0,
            }

        messages = self._build_messages(message)

        chat_model = ChatOpenAI(
            model=self.model,
            temperature=self.temperature,
        )

        with get_openai_callback() as cb:
            resp = chat_model.invoke(messages)

        content = getattr(resp, "content", str(resp))

        return {
            "response": content,
            "tokens_prompt": cb.prompt_tokens,
            "tokens_completion": cb.completion_tokens,
            "tokens_total": cb.total_tokens,
            "cost_usd": cb.total_cost,
        }


# =============================================================================
# Agent Manager
# =============================================================================
class AgentManager:
    """
    Manager responsible for instantiating and coordinating multiple agents.

    Parameters
    ----------
    config_path : Path
        Path to the JSON configuration containing agent definitions.
    prompt_dir : Path
        Directory containing prompt template files.
    short_term_memory_provider : MemoryProvider
        Shared short-term memory provider for all agents.
    long_term_memory_provider : MemoryProvider
        Shared long-term memory provider for all agents.
    context_text : str, optional
        Static context shared across all agents.

    Attributes
    ----------
    agents : dict
        Mapping of agent names to Agent instances.
    """

    def __init__(
        self,
        config_path: Path,
        prompt_dir: Path,
        short_term_memory_provider: MemoryProvider,
        long_term_memory_provider: MemoryProvider,
        context_text: Optional[str] = None,
    ):
        self.prompt_dir = prompt_dir
        self.config = FileUtils.read_json(config_path)
        self.short_term_memory_provider = short_term_memory_provider
        self.long_term_memory_provider = long_term_memory_provider
        self.context_text = context_text
        self.agents = {}
        self._load_agents()

    def _load_agents(self) -> None:
        """
        Initialize all agents defined in the configuration file.
        """
        for section in ("brain_agents", "tool_agents"):
            for name, cfg in self.config.get(section, {}).items():
                self.agents[name] = Agent(
                    name=name,
                    config=cfg,
                    prompt_dir=self.prompt_dir,
                    short_term_memory_provider=self.short_term_memory_provider,
                    long_term_memory_provider=self.long_term_memory_provider,
                    context_text=self.context_text,
                )

    def run(self, agent_name: str, message: Any) -> Dict[str, Any]:
        """
        Execute a specific agent with the given message.

        Parameters
        ----------
        agent_name : str
            Name of the agent to execute.
        message : Any
            Input message.

        Returns
        -------
        dict
            Agent response.

        Raises
        ------
        ValueError
            If the agent does not exist.
        """
        if agent_name not in self.agents:
            raise ValueError(f"Agente '{agent_name}' não encontrado")

        return self.agents[agent_name].run(message)
