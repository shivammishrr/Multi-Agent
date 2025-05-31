import os
from pathlib import Path
from typing import Optional

import toml
from pydantic import BaseModel
from dotenv import load_dotenv

# Define the path to the root of the project (one level up from core)
PROJECT_ROOT = Path(__file__).parent.parent

class Settings(BaseModel):
    # API Keys
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    TAVILY_API_KEY: Optional[str] = None

    # Model Names
    OPENAI_MODEL_NAME: str = "gpt-3.5-turbo"
    ANTHROPIC_MODEL_NAME: str = "claude-2"

    # Agent Settings
    AGENT_NAME: str = "MyLangGraphAgent"

    # Add other settings as needed

    class Config:
        env_file = ".env" # Though we primarily load from toml and then override with env vars
        extra = "ignore" # Ignore extra fields from toml or env

def load_settings() -> Settings:
    # Load environment variables from .env file first (if it exists)
    load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

    # Determine path to settings.toml
    # Assumes settings.toml is in the config directory, which is at the same level as core
    config_file_path = PROJECT_ROOT / "config" / "settings.toml"

    config_data = {}
    if config_file_path.exists():
        try:
            config_data = toml.load(config_file_path)
        except toml.TomlDecodeError as e:
            print(f"Error decoding {config_file_path}: {e}")
            # Decide if you want to raise an error or proceed with defaults/env vars only

    # Prepare data for Pydantic model, prioritizing environment variables
    # Pydantic automatically reads environment variables if the field name matches
    # and they are not explicitly passed in the init call.
    # However, to ensure our specific loading order (toml -> env),
    # we can manually build the dict for Pydantic.

    # Start with TOML data
    initial_settings = {k.lower(): v for k, v in config_data.items()}

    # Override with environment variables if they exist
    # Pydantic's Settings class does this automatically if env_prefix is set,
    # but here we are explicit for clarity with TOML.
    # We can iterate through model fields and check os.environ.

    # For simplicity, we'll let Pydantic handle .env and direct env vars.
    # The values from config_data (toml) will be used if not found in env.
    # Pydantic v2 prioritizes init_vars > env_vars > model_defaults.
    # So we load toml into init_vars.

    # Create a dictionary from TOML, ensuring keys are lowercase to match Pydantic fields
    toml_values = {}
    if config_data:
        for section, values in config_data.items():
            if isinstance(values, dict): # Handle sections like [api_keys]
                 for key, value in values.items():
                    toml_values[key.upper()] = value # Pydantic matches uppercase env vars
            else: # Handle top-level keys
                toml_values[section.upper()] = values


    # Pydantic will load .env and then override with actual environment variables.
    # We then pass toml_values, which will be overridden by any env vars.
    # This isn't quite right. Pydantic loads .env file specified in Config.
    # Then it loads actual env vars.
    # Then it takes explicit kwargs.
    # Let's adjust.

    # 1. Load from TOML
    loaded_from_toml = {}
    if config_data: # config_data is already a dict from toml.load()
        # Assuming settings.toml structure like:
        # OPENAI_API_KEY = "..."
        # ANTHROPIC_API_KEY = "..."
        # or nested, which needs more handling. Let's assume flat for now for simplicity
        # or adapt to the example structure.
        for key, value in config_data.items():
            if isinstance(value, dict): # e.g. a section [MODEL_SETTINGS]
                for k, v in value.items():
                    loaded_from_toml[k.upper()] = v
            else:
                loaded_from_toml[key.upper()] = value


    # 2. Create Settings instance. Pydantic will:
    #    - Apply defaults from model definition
    #    - Override with values from .env file (if env_file is set and file exists)
    #    - Override with actual environment variables
    #    - Override with values passed as kwargs (loaded_from_toml in this case)
    # The order should be: defaults < toml < .env < environment variables < explicit kwargs to Settings()
    # Pydantic's actual order: model_fields_defaults < model_config_from_toml < .env < os_environ < init_kwargs < validate_assignment
    # So, we should load toml, then create Settings object. It will pick up env vars.

    # For Pydantic V2, the `Settings` class from `pydantic_settings` is preferred.
    # Let's stick to BaseModel for now and do it manually.

    settings_kwargs = {}
    # Load from TOML first
    if config_data:
        # Assuming flat structure or simple sections in TOML for this example
        for key_outer, value_outer in config_data.items():
            if isinstance(value_outer, dict):
                for key_inner, value_inner in value_outer.items():
                    settings_kwargs[key_inner.upper()] = value_inner
            else:
                settings_kwargs[key_outer.upper()] = value_outer

    # Now, override with environment variables
    for field_name in Settings.model_fields:
        env_var = os.getenv(field_name.upper())
        if env_var is not None:
            settings_kwargs[field_name.upper()] = env_var

    return Settings(**settings_kwargs)


# Global settings instance
settings = load_settings()

if __name__ == "__main__":
    # Example usage:
    # User should copy settings.example.toml to settings.toml and fill it
    # Or set environment variables
    print("Loaded settings:")
    print(f"  OpenAI API Key: {'*' * 8 if settings.OPENAI_API_KEY else 'Not set'}")
    print(f"  Anthropic API Key: {'*' * 8 if settings.ANTHROPIC_API_KEY else 'Not set'}")
    print(f"  Tavily API Key: {'*' * 8 if settings.TAVILY_API_KEY else 'Not set'}")
    print(f"  OpenAI Model Name: {settings.OPENAI_MODEL_NAME}")
    print(f"  Anthropic Model Name: {settings.ANTHROPIC_MODEL_NAME}")
    print(f"  Agent Name: {settings.AGENT_NAME}")

    # To test environment variable override:
    # Export OPENAI_API_KEY="new_key_from_env" before running
    # For example, in your shell:
    # export OPENAI_API_KEY="env_key_test"
    # export AGENT_NAME="Agent From Env"
    # python core/config_loader.py
    # (Assuming you have a settings.toml in config/ directory)
