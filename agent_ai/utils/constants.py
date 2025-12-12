from pathlib import Path

# Input Guardrail Denied Response
INPUT_GUARDRAIL_DENIED_RESPONSE = "A mensagem está fora das diretrizes do agente. Por favor, tente novamente."

# OpenAI Embedding Prices
OPENAI_EMBEDDING_PRICES = {
    "text-embedding-3-small": 0.02 / 1_000_000,  # USD/token
    "text-embedding-3-large": 0.13 / 1_000_000,  # USD/token
    "text-embedding-ada-002": 0.10 / 1_000_000,  # USD/token
}

# Paths
MODEL_CONFIG_FILE_PATH = Path("agent_ai/config/agent_config.json")
PROMPT_PATH = Path("agent_ai/prompts")
