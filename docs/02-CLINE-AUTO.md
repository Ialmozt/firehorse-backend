🤖 Automated Deployment with Cline

## Setup
1. Open VS Code
2. Press Cmd+K (or Ctrl+K on Windows)
3. Copy prompt from: docs/03-CLINE-PROMPT.txt
4. Paste in Cline
5. Press Enter

## What Cline Will Do
- Create .env file from .env.example
- Deploy schema.sql to PostgreSQL
- Build Docker image
- Start Docker containers
- Run health and webhook tests

## Time
Approximately 10-15 minutes

## Result
- Full working Firehorse MVP
- PostgreSQL connected
- API running on port 8000
- Ready for production

See docs/03-CLINE-PROMPT.txt for the exact prompt to use.