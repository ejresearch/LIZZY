"""Configuration management for screenplay formatter."""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any


class ConfigManager:
    """Manages configuration settings including API keys."""

    def __init__(self):
        self.config_dir = Path.home() / '.screenplay_formatter'
        self.config_file = self.config_dir / 'config.json'
        self.config_dir.mkdir(exist_ok=True)

        # Load existing config
        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

        # Return default config
        return {
            'openai_api_key': None,
            'default_model': 'gpt-5.1',
            'default_confidence': 0.8,
            'strict_validation': False
        }

    def _save_config(self):
        """Save configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self._config, f, indent=2)
        except IOError as e:
            print(f"Warning: Could not save config: {e}")

    def set_openai_api_key(self, api_key: str):
        """Set OpenAI API key."""
        self._config['openai_api_key'] = api_key
        self._save_config()
        print("OpenAI API key saved successfully!")

    def get_openai_api_key(self) -> Optional[str]:
        """Get OpenAI API key from config or environment."""
        # Priority: environment variable > config file
        return os.getenv('OPENAI_API_KEY') or self._config.get('openai_api_key')

    def remove_openai_api_key(self):
        """Remove stored OpenAI API key."""
        self._config['openai_api_key'] = None
        self._save_config()
        print("OpenAI API key removed from config")

    def has_api_key(self) -> bool:
        """Check if API key is available."""
        return self.get_openai_api_key() is not None

    def set_default_model(self, model: str):
        """Set default OpenAI model."""
        self._config['default_model'] = model
        self._save_config()

    def get_default_model(self) -> str:
        """Get default OpenAI model."""
        return self._config.get('default_model', 'gpt-5.1')

    def set_default_confidence(self, confidence: float):
        """Set default confidence threshold."""
        if 0.0 <= confidence <= 1.0:
            self._config['default_confidence'] = confidence
            self._save_config()
        else:
            raise ValueError("Confidence must be between 0.0 and 1.0")

    def get_default_confidence(self) -> float:
        """Get default confidence threshold."""
        return self._config.get('default_confidence', 0.8)

    def set_strict_validation(self, strict: bool):
        """Set strict validation mode."""
        self._config['strict_validation'] = strict
        self._save_config()

    def get_strict_validation(self) -> bool:
        """Get strict validation setting."""
        return self._config.get('strict_validation', False)

    def show_config(self) -> str:
        """Show current configuration."""
        lines = []
        lines.append("Current Configuration:")
        lines.append("-" * 30)

        api_key = self.get_openai_api_key()
        if api_key:
            masked_key = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "***"
            lines.append(f"OpenAI API Key: {masked_key}")
        else:
            lines.append("OpenAI API Key: Not set")

        lines.append(f"Default Model: {self.get_default_model()}")
        lines.append(f"Default Confidence: {self.get_default_confidence()}")
        lines.append(f"Strict Validation: {self.get_strict_validation()}")
        lines.append("")
        lines.append(f"Config file: {self.config_file}")

        return '\n'.join(lines)

    def reset_config(self):
        """Reset configuration to defaults."""
        self._config = {
            'openai_api_key': None,
            'default_model': 'gpt-5.1',
            'default_confidence': 0.8,
            'strict_validation': False
        }
        self._save_config()
        print("Configuration reset to defaults")


# Global config instance
config_manager = ConfigManager()