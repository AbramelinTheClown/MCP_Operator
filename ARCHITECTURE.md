# MCP Operator Architecture

## Containerization Strategy
```mermaid
graph LR
    A[Tool Container] --> B[Isolated Python Environment]
    A --> C[Tool-Specific Dependencies]
    A --> D[Port Mapping]
    
    E[Host Machine] --> F[docker-compose]
    F --> A
    F --> G[Another Tool Container]
```

## File Descriptions
| File | Purpose | Owner |
|------|---------|-------|
| `docker-compose.yml` | Orchestrate multiple MCP services | DevOps Agent |
| `Dockerfile.*` | Tool-specific container builds | Code Agent |
| `src/mcp_tools/` | Core Python package structure | Code Agent |