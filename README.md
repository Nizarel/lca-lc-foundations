# 🔗 Introduction to LangChain - Python

## Introduction

Welcome to LangChain Academy's **Introduction to LangChain** course!

This repository is the companion to the course located [HERE](https://academy.langchain.com/courses/foundation-introduction-to-langchain-python).

---

## 🚀 Setup

### Prerequisites

- The [Chrome](https://www.google.com/chrome/) browser is recommended
- [git](https://git-scm.com/install/) is recommended
- A package/project manager: [uv](https://docs.astral.sh/uv/) (recommended) or [pip](https://pypi.org/project/pip/)
- note: `uv` is also required in Module 2, Lesson 1 to run the MCP server with `uvx`
- The course requires Python >=3.12, <3.14  If you use `uv`, it will take care of this for you. [More info](#python-virtual-environments)

### Installation

Download the course repository
```bash
# Clone the repo
git clone --depth 1 https://github.com/langchain-ai/lca-lc-foundations.git
cd lca-lc-foundations
```

Make a copy of example.env
```bash
# Create .env file
cp example.env .env
```

Edit the .env file to include the keys below for [Models](#model-providers) and optionally [LangSmith](#getting-started-with-langsmith)

- Get your Azure OpenAI resource key and deployment name from [Microsoft Foundry](https://ai.azure.com/).
- Optional provider examples use an Anthropic API Key [here](https://console.anthropic.com) and a Google API Key [here](https://ai.google.dev/gemini-api/docs/quickstart). The dynamic-model lesson also uses Anthropic.
- Optional, Create a [LangSmith](https://smith.langchain.com/) account and API Key.  

```bash
# Manual installs for checking: uv

# Required
AZURE_OPENAI_API_KEY='your_azure_openai_api_key_here'
AZURE_OPENAI_ENDPOINT='https://manadry.cognitiveservices.azure.com/'
OPENAI_API_VERSION='2024-12-01-preview'
AZURE_OPENAI_DEPLOYMENT='gpt-6.1-sol'
TAVILY_API_KEY='your_tavily_api_key_here'

# Optional deployments for the bonus RAG and audio lessons
# AZURE_OPENAI_EMBEDDING_DEPLOYMENT='your_text_embedding_3_large_deployment'
# AZURE_OPENAI_AUDIO_DEPLOYMENT='your_audio_deployment'

# Optional provider examples in Module 1 and dynamic models in Module 3
ANTHROPIC_API_KEY='your_anthropic_api_key_here'
GOOGLE_API_KEY='your_google_api_key_here'

# Optional for evaluation and tracing
LANGSMITH_API_KEY='your_langsmith_api_key_here'
# uncomment to set tracing to true when you set up your LangSmith account
#LANGSMITH_TRACING=true
LANGSMITH_PROJECT=lca-lc-foundation
# Uncomment the following if you are on the EU instance:
#LANGSMITH_ENDPOINT=https://eu.api.smith.langchain.com
```


Make a virtual environment and install dependencies. [More info](#python-virtual-environments)

<details open>
<summary>Using uv (recommended)</summary>

```bash
uv sync
```

</details>

<details>
<summary>Using pip</summary>

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

</details>

### Setup Verification

After completing the Setup section, we recommend you run the following command to verify your environment.

<details open>
<summary>Using uv</summary>

```bash
uv run python env_utils.py
```

</details>

<details>
<summary>Using pip</summary>

```bash
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
python env_utils.py
```

</details>

[If the script flags issues, see this section below.](#setup-verification-issues)

Offline configuration tests (no API keys or Azure requests required):

```bash
uv run python -m unittest discover -s tests
```

### Run Notebooks [More Info](#development-environment)

<details open>
<summary>Using uv (recommended)</summary>

```bash
uv run jupyter lab
```

</details>

<details>
<summary>Using pip</summary>

```bash
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
jupyter lab
```

</details>

### Run Studio (optional)

Ensure you are in the notebooks/module-1 or notebooks/module-3 directory

 <details open>
<summary>Using uv (recommended)</summary>

```bash
uv run langgraph dev
```

</details>

<details>
<summary>Using pip</summary>

```bash
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
langgraph dev
```

</details>

## 📚 Lessons
This repository contains three Modules that serve as introductions to many of LangChain's most-used features.

---

### Module 1: Create Agent

- Foundational models
- Tools
- Short-Term Memory
- Multimodal Messages
- Project: Personal Chef

### Module 2: Advanced Agent

- Model Context Protocol (MCP)
- Context and State
- Multi-Agent Systems
- Project: Wedding Planner

### Module 3: Production-Ready Agent

- What is Middleware?
- Managing Long Conversations
- Human In The Loop (HITL)
- Dynamic Agents
- Project: Email Assistant
- Bonus: Agent Chat UI

## 📖 Related Resources

### Setup Verification Issues

**What the verification procedure checks:**
- ✅ Python executable location and version (must be >=3.12, <3.14)
- ✅ Virtual environment is properly activated
- ✅ Required packages are installed with correct versions
- ✅ Packages are in the correct Python version's site-packages
- ✅ Environment variables (API keys) are properly configured

**Configuration Issues and Solutions:**

<details>
<summary>ImportError when running env_utils.py</summary>

If you see an error like `ModuleNotFoundError: No module named 'dotenv'`, you're likely running Python outside the virtual environment.

**Solution:**
- Use `uv run python env_utils.py` (recommended), or
- Activate the virtual environment first:
  - macOS/Linux: `source .venv/bin/activate`
  - Windows: `.venv\Scripts\activate`

</details>

<details>
<summary>Environment Variable Conflicts</summary>

If you see a warning about "ENVIRONMENT VARIABLE CONFLICTS DETECTED", you have API keys set in your system environment that differ from your .env file. Since `load_dotenv()` doesn't override existing variables by default, your system values will be used.

**Solutions:**
1. Do nothing and accept the system environment variable value
2. Unset the conflicting system environment variables for this shell session (commands provided in warning)
3. Use `load_dotenv(override=True)` in your notebooks to force .env values to take precedence
4. Update your .env file or shell init so the values are in agreement

</details>

<details>
<summary>LangSmith Tracing Errors</summary>

If you see "LANGSMITH_TRACING is enabled but LANGSMITH_API_KEY still has the example/placeholder value", you need to either:
1. Set a valid LangSmith API key in your .env file, or
2. Comment out or set `LANGSMITH_TRACING=false` in your .env file

Note: LangSmith is optional for evaluation and tracing. The course works without it.

</details>

<details>
<summary>Wrong Python Version</summary>

If you see a warning about Python version not satisfying requirements, you need Python >=3.12 and <3.14.

**Solution:**
- If using `uv`: Run `uv sync` which will automatically install the correct Python version
- If using pip: Install Python 3.12 or 3.13 using [pyenv](#python-virtual-environments) or from [python.org](https://www.python.org/downloads/)

</details>

### Python Virtual Environments

Managing your Python version is often best done with virtual environments. This allows you to select a Python version for the course independent of the system Python version.

<details open>
<summary>Using uv (recommended)</summary>

`uv` will install a version of Python compatible with the versions specified in the `pyproject.toml` in the `.venv` directory when running the `uv sync` specified above. It will use this version when invoking with `uv run`. For additional information, please see [uv](https://docs.astral.sh/uv/).
</details>

<details>
<summary>Using pyenv + pip</summary>

If you are using pip instead of uv, you may prefer using pyenv to manage your Python versions. For additional information, please see [pyenv](https://github.com/pyenv/pyenv).

```bash
pyenv install 3.12
pyenv local 3.12
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

</details>

### Model Providers

The OpenAI examples use **Azure OpenAI in Microsoft Foundry** through LangChain's `AzureChatOpenAI`, backed by the OpenAI SDK's `AzureOpenAI` client. Set `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `OPENAI_API_VERSION`, and `AZURE_OPENAI_DEPLOYMENT` in `.env`. The configured endpoint is `https://manadry.cognitiveservices.azure.com/`, the API version is `2024-12-01-preview`, and the chat deployment is `gpt-6.1-sol`. Use your actual **deployment name**, which can differ from the underlying model name. A public OpenAI API key is not needed.

`AzureChatOpenAI` reads the endpoint, key and API version from these environment variables automatically:

```python
import os
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI

load_dotenv()
model = AzureChatOpenAI(
    azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT"],
)
```

For direct SDK calls, the equivalent configuration is:

```python
from openai import AzureOpenAI

client = AzureOpenAI(
    api_version=os.environ["OPENAI_API_VERSION"],
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
)
response = client.chat.completions.create(
    model=os.environ["AZURE_OPENAI_DEPLOYMENT"],
    messages=[{"role": "user", "content": "Hello!"}],
)
```

The bonus RAG lesson additionally requires `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`, pointing to a `text-embedding-3-large` deployment. The audio section of the multimodal lesson requires `AZURE_OPENAI_AUDIO_DEPLOYMENT`, pointing to an audio-capable chat deployment supported by your Azure resource and API version. Only run those sections after configuring the corresponding deployment. Image, tool-calling and structured-output examples likewise require a chat deployment supporting those capabilities.

Anthropic and Google examples are unchanged. Obtain their own API keys from [Anthropic](https://console.anthropic.com) or [Google](https://ai.google.dev/gemini-api/docs/quickstart) to run those cells. In the foundational-model lesson, the provider examples reassign `model`; re-run the Azure initialization cell before the agent example to use Foundry. The dynamic-model lesson intentionally switches between the Foundry deployment and Anthropic.

This course has been created using particular models and model providers.  You can use other providers, but you will need to update the API keys in the .env file and make some necessary code changes. LangChain supports many chat model providers. [More Info](https://docs.langchain.com/oss/python/integrations/providers/all_providers).

Tavily is a search provider that returns search results in an LLM-friendly way. They have a generous free tier. [Tavily](https://tavily.com)

### Getting Started with LangSmith

- Create a [LangSmith](https://smith.langchain.com/) account
- Create a LangSmith API key

<img width="600" alt="LangSmith Dashboard" src="https://github.com/user-attachments/assets/e39b8364-c3e3-4c75-a287-d9d4685caad5" />

<img width="600" alt="LangSmith API Keys" src="https://github.com/user-attachments/assets/2e916b2d-e3b0-4c59-a178-c5818604b8fe" />

- Update the .env file you created with your new LangSmith API Key.
- Check that LANGSMITH_TRACING is uncommented and set to true.

For more information on LangSmith, see our docs [here](https://docs.langchain.com/langsmith/home).

**Note:** If you enable LangSmith tracing by setting `LANGSMITH_TRACING=true` in your .env file, make sure you have a valid `LANGSMITH_API_KEY` set. The environment verification script (`env_utils.py`) will warn you if tracing is enabled without a valid key.

### Environment Variables

This course uses the [dotenv](https://pypi.org/project/python-dotenv) module to read key-value pairs from the .env file and set them in the environment in the Jupyter notebooks. They do not need to be set globally in your system environment.

**Note:** If you have API keys already set in your system environment, they may conflict with the ones in your .env file. The `env_utils.py` verification script will detect and warn you about such conflicts. By default, `load_dotenv()` does not override existing environment variables.


### Development Environment

The course uses [Jupyter](https://jupyter.org/) notebooks. The Jupyter package is installed in the virtual environment and can be run as described above. Jupyter notebooks can also be edited and run in VSCode or other VSCode variants such as Windsurf or Cursor.
