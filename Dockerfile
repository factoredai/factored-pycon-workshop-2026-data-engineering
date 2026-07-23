FROM apache/airflow:3.0.1-python3.11

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# LLM SDKs so the DAG can use Live LLM Mode inside the container when an API key
# is provided (openai also covers OpenRouter's OpenAI-compatible endpoint).
# Harmless when no key is set: the pipeline stays on canned responses.
RUN pip install --no-cache-dir openai anthropic
