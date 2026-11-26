import os

# Prevent LiteLLM's optional model-price refresh during offline protocol tests.
os.environ.setdefault('LITELLM_LOCAL_MODEL_COST_MAP', 'True')
