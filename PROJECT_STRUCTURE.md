# MCP Operator Modular Architecture

```text
mcp_operator/
├── docker-compose.yml
├── Dockerfile.<tool_name>  
├── requirements.<tool_name>.txt 
├── src/
│   └── mcp_tools/
│       ├── __init__.py       
│       ├── <tool_name_1>/    
│       │   ├── __init__.py   
│       │   ├── tools.py      
│       │   └── server.py     
│       ├── <tool_name_2>/    
│       │   ├── __init__.py
│       │   ├── tools.py
│       │   └── server.py
│       └── ...
├── .env.example            
└── README.md               
```

## Architectural Decisions

### Dependency Isolation
- **Per-tool requirements**: Each tool maintains its own `requirements.<tool_name>.txt`
- **Dockerized environments**: Tool-specific Dockerfiles ensure isolated Python installations
- **Prevent cross-tool imports**: Code separation enforces explicit MCP protocol communication

### Poetry Consideration
```text
[tool.poetry]
name = "mcp_tool_example"
version = "0.1.0"

[tool.poetry.dependencies]
python = "^3.10"
modelcontextprotocol = "^1.0"
```

**Decision Rationale**:
- ✅ **Current Approach**: requirements.txt + Docker isolation provides simplicity
- 🔜 **Future Consideration**: Poetry for per-tool dependency resolution if complexity increases
- **Tradeoff**: Loose coupling vs centralized management

## Conflict Avoidance Mechanisms

1. **Dependency Conflicts**:
   - Isolated container environments allow conflicting versions
   - No shared Python packages between tools

2. **Code Conflicts**:
   - Physical separation of tool implementations
   - Protocol-based communication instead of direct imports
   - Independent version control histories per tool

## Implementation Roadmap

1. Phase 1 (Current): requirements.txt based per-tool dependencies
2. Phase 2: Evaluate dependency conflict frequency
3. Phase 3: Poetry adoption for tools with complex requirements