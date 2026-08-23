"""
Reference data for AI setup: known providers, the env vars litellm reads for
each, and a best-effort (non-exhaustive) list of models per provider.

Model names go stale fast - this is a helpful menu, not a hard whitelist.
Provider keys match litellm's `provider/model` naming convention exactly
(see litellm.types.utils.LlmProviders) - keep in sync if that changes.
"""

# env vars litellm reads per provider
PROVIDER_ENV_VARS = {
    "openai": ["OPENAI_API_KEY"],
    "anthropic": ["ANTHROPIC_API_KEY"],
    "gemini": ["GEMINI_API_KEY"],
    "vertex_ai": ["VERTEXAI_PROJECT", "VERTEXAI_LOCATION", "GOOGLE_APPLICATION_CREDENTIALS"],
    "groq": ["GROQ_API_KEY"],
    "mistral": ["MISTRAL_API_KEY"],
    "together_ai": ["TOGETHERAI_API_KEY"],
    "xai": ["XAI_API_KEY"],
    "deepseek": ["DEEPSEEK_API_KEY"],
    "cohere": ["COHERE_API_KEY"],
    "fireworks_ai": ["FIREWORKS_AI_API_KEY"],
    "nebius": ["NEBIUS_API_KEY"],
    "sambanova": ["SAMBANOVA_API_KEY"],
    "huggingface": ["HUGGINGFACE_API_KEY"],
    "azure": ["AZURE_API_KEY", "AZURE_API_VERSION", "AZURE_API_BASE"],
    "bedrock": ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION_NAME"],
    "watsonx": ["WATSONX_API_KEY", "WATSONX_PROJECT_ID", "WATSONX_URL"],
    "cerebras": ["CEREBRAS_API_KEY"],
    "inception": ["INCEPTION_API_KEY"],
    "ollama": ["OLLAMA_API_BASE"],
}

# example/known models per provider - not exhaustive, just a menu to pick from
# or type past (e.g. a newer model the provider has added since this was written)
PROVIDER_MODELS = {
    "openai": ["gpt-5", "gpt-4o", "gpt-4o-mini", "o3", "o3-mini"],
    "anthropic": ["claude-opus-5", "claude-sonnet-5", "claude-haiku-4-5-20251001", "claude-fable-5"],
    "gemini": ["gemini-3.7-flash", "gemini-3.1-pro-preview", "gemini-3.6-flash", "gemini-3.5-flash-lite", "gemini-2.5-pro"],
    "vertex_ai": ["gemini-3.7-flash", "gemini-3.1-pro-preview", "gemini-3.6-flash", "gemini-2.5-pro"],
    "groq": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768", "gemma2-9b-it"],
    "mistral": ["mistral-large-latest", "mistral-small-latest", "codestral-latest", "pixtral-large-latest"],
    "together_ai": ["meta-llama/Llama-3.3-70B-Instruct-Turbo", "Qwen/Qwen2.5-72B-Instruct-Turbo", "deepseek-ai/DeepSeek-V3"],
    "xai": ["grok-4", "grok-4-fast", "grok-3", "grok-3-mini"],
    "deepseek": ["deepseek-chat", "deepseek-reasoner"],
    "cohere": ["command-a", "command-r-plus", "command-r"],
    "fireworks_ai": ["accounts/fireworks/models/llama-v3p3-70b-instruct", "accounts/fireworks/models/deepseek-v3"],
    "nebius": ["meta-llama/Llama-3.3-70B-Instruct", "Qwen/Qwen2.5-72B-Instruct"],
    "sambanova": ["Meta-Llama-3.3-70B-Instruct", "Meta-Llama-3.1-8B-Instruct"],
    "huggingface": ["meta-llama/Llama-3.3-70B-Instruct", "mistralai/Mixtral-8x7B-Instruct-v0.1"],
    "azure": [],  # model choice is your own Azure deployment name, not a fixed list
    "bedrock": ["anthropic.claude-3-5-sonnet-20241022-v2:0", "meta.llama3-1-70b-instruct-v1:0", "amazon.titan-text-premier-v1:0"],
    "watsonx": ["ibm/granite-3-8b-instruct", "meta-llama/llama-3-3-70b-instruct"],
    "cerebras": ["llama-3.3-70b", "llama3.1-8b"],
    "inception": ["mercury-coder-small"],
    "ollama": [],  # whatever model you've pulled locally, e.g. "llama3"
}
