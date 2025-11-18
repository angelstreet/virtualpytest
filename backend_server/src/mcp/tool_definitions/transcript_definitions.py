"""Transcript tool definitions for audio transcription"""

from typing import List, Dict, Any


def get_tools() -> List[Dict[str, Any]]:
    """Get transcript-related tool definitions"""
    return [
        {
            "name": "get_transcript",
            "description": "Get audio transcript from device with optional translation.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "device_id": {"type": "string", "description": "Device identifier (optional - defaults to 'device_1')"},
                    "team_id": {"type": "string", "description": "Team ID for security (optional - uses default if omitted)"},
                    "chunk_url": {"type": "string", "description": "Chunk URL (provide this OR hour+chunk_index)"},
                    "hour": {"type": "integer", "description": "Hour number (use with chunk_index)"},
                    "chunk_index": {"type": "integer", "description": "Chunk index (use with hour)"},
                    "target_language": {"type": "string", "description": "Language code for translation (e.g., 'fr', 'es', 'de')"}
                },
                "required": []
            }
        }
    ]

