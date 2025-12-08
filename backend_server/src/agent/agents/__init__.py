"""
Agent Definitions

NOTE: Python agent classes have been removed.
The system uses YAML-driven agents loaded from registry/templates/*.yaml

All agent behavior is defined in YAML:
- qa-mobile-manager.yaml (Scout)
- qa-web-manager.yaml (Sherlock)
- qa-stb-manager.yaml (Watcher)
- ai-assistant.yaml (Atlas)
- monitoring-manager.yaml (Guardian)

See core/manager.py for the QAManagerAgent that loads and runs YAML configs.
"""

__all__ = []
