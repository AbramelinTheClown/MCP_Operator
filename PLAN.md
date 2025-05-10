# MCP Operator Project Plan

## MVP Definition
- Core Features:
  - Multiple isolated MCP tool services
  - Docker-based deployment
  - Poetry dependency management
  - Modular architecture

## System Architecture
```mermaid
graph TD
    A[mcp_operator] --> B[docker-compose.yml]
    A --> C[src/mcp_tools]
    C --> D[Tool1]
    C --> E[Tool2]
    D --> F[__init__.py]
    D --> G[tools.py]
    D --> H[server.py]
```

## Project Structure
[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)

## Initial Setup
1. `poetry init`
2. `docker-compose build`
3. `cp .env.example .env`