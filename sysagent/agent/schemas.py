"""
sysagent/agent/schemas.py

OpenAI function calling schemas for the SysAgent tools.
These define the API contract between the LLM and our Python tools.
"""

# The complete list of available tools to send to the OpenAI API
SYSAGENT_TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_system_metrics",
            "description": "Returns a snapshot of the host system's vital signs including CPU percent, RAM, Swap, load average, and uptime. Call this first to get a broad overview of system health.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_processes",
            "description": "Returns a list of the top consuming processes. Crucial for diagnosing 'server is slow' or OutOfMemory complaints.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sort_by": {
                        "type": "string",
                        "description": "What to sort by. Must be exactly 'cpu' or 'memory'.",
                        "enum": ["cpu", "memory"]
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of processes to return. Cap it at 10 to save context space."
                    }
                },
                "required": ["sort_by"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_journal_tail",
            "description": "Reads the most recent lines from the systemd journal logs. Use this to find out why a service crashed, check OOM killer events, or review recent system errors.",
            "parameters": {
                "type": "object",
                "properties": {
                    "unit": {
                        "type": "string",
                        "description": "Optional systemd unit name to filter by (e.g., 'nginx.service' or 'docker.service'). Omit to read global system logs."
                    },
                    "lines": {
                        "type": "integer",
                        "description": "Number of lines to return. Default 50. Max 200."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_knowledge_base",
            "description": "Performs a semantic search against the Linux documentation RAG database. Call this whenever you encounter unfamiliar error codes, kernel parameters, or command flags.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The natural language question or term to look up (e.g., 'OOM killer process selection algorithm')."
                    }
                },
                "required": ["query"]
            }
        }
    }
]
