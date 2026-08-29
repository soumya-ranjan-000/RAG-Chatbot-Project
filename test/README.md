# DeepEval Testing & Evaluation Suite

This directory contains configuration, environment templates, and test suites for evaluating the **RAG Pipeline** and **Airline Booking Agent** using **[DeepEval](https://github.com/confident-ai/deepeval)** (v4.2.0).

---

## 📁 Directory Structure

```
test/
├── .env                  # Active environment variables & API keys (gitignored)
├── .env.example          # Template with documentation for all required keys
├── config.py             # Central DeepEval settings, metric factories & LLM judge resolution
├── conftest.py           # Pytest fixtures and test environment setup
├── test_rag_eval.py      # Sample DeepEval test suite (Faithfulness, Relevancy, G-Eval)
└── README.md             # Usage guide & configuration documentation
```

---

## ⚙️ Configuration & Environment Variables

### 1. Set Up Your Keys in `test/.env`

Copy `test/.env.example` to `test/.env` (or edit `test/.env` directly):

```bash
cp test/.env.example test/.env
```

Fill in the necessary values:

| Variable | Description | Default / Example |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI API key for evaluation judge model | `sk-...` |
| `OPENAI_MODEL_NAME` | Model used to compute metrics | `gpt-4o-mini` / `gpt-4o` |
| `OPENAI_EMBEDDING_MODEL_NAME` | Embedding model for synthesizer | `text-embedding-3-small` |
| `CONFIDENT_API_KEY` | (Optional) Confident AI platform key for dashboard tracking | `...` |
| `DEEPEVAL_CONFIDENT_REGION` | Confident AI platform region | `US` or `EU` |
| `DEEPEVAL_VERBOSE_MODE` | Detailed terminal output | `YES` |
| `DEEPEVAL_METRIC_VERBOSE` | Step-by-step scoring rationale printout | `YES` |
| `DEEPEVAL_TELEMETRY_OPT_OUT` | Opt out of anonymous telemetry | `NO` |
| `SUPABASE_URL` | Supabase URL for live vector database testing | `https://...supabase.co` |
| `SUPABASE_KEY` | Supabase API key | `eyJ...` |
| `PSS_API_URL` | Passenger Service System API URL | `http://localhost:8000/api/pss` |

---

## 🚀 Running Evaluations

### Using the DeepEval CLI:

```bash
# Run all evaluation tests in the test directory
test/.venv/bin/deepeval test run test/test_rag_eval.py

# Or if the virtual environment is activated:
source test/.venv/bin/activate
deepeval test run test/test_rag_eval.py
```

### Using Pytest:

```bash
test/.venv/bin/pytest test/test_rag_eval.py -v -s
```

---

## 🧠 Supported Evaluator LLM Providers

DeepEval uses an LLM judge to compute metrics such as **Faithfulness**, **Answer Relevancy**, **Contextual Relevancy**, and **G-Eval**.

### 1. OpenAI (Default)
```env
USE_OPENAI_MODEL=YES
OPENAI_API_KEY=sk-...
OPENAI_MODEL_NAME=gpt-4o-mini
```

### 2. Google Gemini
```env
USE_GEMINI_MODEL=YES
GEMINI_API_KEY=your-gemini-key
GEMINI_MODEL_NAME=gemini-1.5-flash
```

### 3. Anthropic Claude
```env
USE_ANTHROPIC_MODEL=YES
ANTHROPIC_API_KEY=your-anthropic-key
ANTHROPIC_MODEL_NAME=claude-3-5-sonnet-20241022
```

### 4. Local LM Studio / Ollama (OpenAI-compatible)
```env
USE_LOCAL_MODEL=YES
LOCAL_MODEL_NAME=qwen2.5-7b-instruct
LOCAL_MODEL_BASE_URL=http://localhost:1234/v1
```

---

## 📊 Pre-Configured Metrics in `config.py`

| Metric Factory | Description | Default Threshold |
|---|---|---|
| `get_faithfulness_metric()` | Checks if the output has factual inconsistencies / hallucinations vs. context | `0.70` |
| `get_answer_relevancy_metric()` | Checks if the output directly answers the user's question | `0.70` |
| `get_contextual_relevancy_metric()` | Checks if the retrieved chunks are relevant to the input query | `0.70` |
| `get_contextual_precision_metric()` | Evaluates ranking quality of retrieved context chunks | `0.70` |
| `get_contextual_recall_metric()` | Measures whether all necessary facts from context were retrieved | `0.70` |
| `get_hallucination_metric()` | Measures hallucination score against ground truth context | `0.50` |
| `get_geval_metric(...)` | Custom multi-criteria rubric evaluation | `0.70` |
| `get_rag_triad_metrics()` | Returns the complete RAG Triad (Relevancy, Faithfulness, Contextual Relevancy) | `0.70` |

