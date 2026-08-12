# ============================================================
# DISCOVERY SYSTEM - QUICK REFERENCE
# ============================================================

# Test discovery agent intelligence (model, Perplexity config, tool descriptions)
.\.venv\Scripts\python.exe test_discovery_intelligence.py

# View recent reports with all details
.\.venv\Scripts\python.exe scripts\view_discovery_reports.py

# View aggregated insights across all runs
.\.venv\Scripts\python.exe scripts\view_discovery_reports.py --insights

# View last 20 reports
.\.venv\Scripts\python.exe scripts\view_discovery_reports.py --limit 20

# Get raw JSON
.\.venv\Scripts\python.exe scripts\view_discovery_reports.py --json

# Check database status (reports, issues, embeddings, events)
.\.venv\Scripts\python.exe check_db_status.py

# Check event collection
.\.venv\Scripts\python.exe check_events.py

# Check rankings/leaderboard
.\.venv\Scripts\python.exe check_rankings.py

# ============================================================
# ISSUE DELETION (CASCADE deletes components/events/embeddings/rankings)
# ============================================================

# List all issues with their IDs
.\.venv\Scripts\python.exe delete_issues.py list

# Show what will be deleted for an issue (dry-run)
.\.venv\Scripts\python.exe delete_issues.py show iss-0001

# Delete one issue (dry-run first, then add --yes)
.\.venv\Scripts\python.exe delete_issues.py delete iss-0001
.\.venv\Scripts\python.exe delete_issues.py delete iss-0001 --yes

# Delete ALL issues (dry-run first, requires confirmation)
.\.venv\Scripts\python.exe delete_issues.py delete-all
.\.venv\Scripts\python.exe delete_issues.py delete-all --yes

# ============================================================
# SERVER & DISCOVERY COMMANDS
# ============================================================

# Restart server (in one terminal)
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload

# Trigger discovery with specific topic (in another terminal)
Invoke-WebRequest -Uri http://localhost:8000/api/discovery `
  -Method POST `
  -Headers @{"Content-Type"="application/json"} `
  -Body '{"topic": "renewable energy", "target_issue_count": 3}' `
  -UseBasicParsing

# Trigger autonomous discovery (no topic)
Invoke-WebRequest -Uri http://localhost:8000/api/discovery `
  -Method POST `
  -Headers @{"Content-Type"="application/json"} `
  -Body '{"topic": "", "target_issue_count": 5}' `
  -UseBasicParsing