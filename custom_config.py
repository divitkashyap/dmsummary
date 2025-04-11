# custom_config.py
from portia.config import default_config, PLANNING_DEFAULT_MODEL_KEY, DEFAULT_MODEL_KEY, LLMModel

def get_my_config():
    config = default_config(
        llm_model_name="GPT_3_5_TURBO",  # Override the model used
        llm_provider="OPENAI",  # Make sure to set the correct provider if needed
        # Other overrides as needed...
    )
    config.models[PLANNING_DEFAULT_MODEL_KEY] = LLMModel.GPT_3_5_TURBO
    config.models[DEFAULT_MODEL_KEY] = LLMModel.GPT_3_5_TURBO
    return config
