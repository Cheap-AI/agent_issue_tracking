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



  # Trigger autonomous discovery (no topic)
Invoke-WebRequest -Uri  https://agent-issue-tracking.onrender.com/api/discovery `
  -Method POST `
  -Headers @{"Content-Type"="application/json"} `
  -Body '{"topic": "", "target_issue_count": 5}' `
  -UseBasicParsing


  So my service is now live. now I want to quickly build the frontend but I am not sure if it will work at all. I want the frontend homepage to show each issue in card, including the title and metrics (impact, scope, recency, etc). When user hovers (with another window or picture in picture) or clicks (into a new page), I want it to show the events related to it (matching the same issue id, chronological order). Can you do this? I have no idea how frontend is wired.

  ## USAGE REPORTS

  # Get last 10 discovery reports (default)
$reports = Invoke-RestMethod -Uri "https://agent-issue-tracking.onrender.com/api/discovery/reports" -Method Get
$reports.reports | Format-Table report_id, issues_created_count, api_usage, created_at

# Get last 20 reports
$reports = Invoke-RestMethod -Uri "https://agent-issue-tracking.onrender.com/api/discovery/reports?limit=20" -Method Get
$reports.reports | Select-Object -First 5 | Format-List

# View full report details
$reports.reports[0] | ConvertTo-Json -Depth 1


##USAGE LEADERBOARD

# Get top 50 issues with metrics (severity, impact, scale, recency)
$leaderboard = Invoke-RestMethod -Uri "https://agent-issue-tracking.onrender.com/api/leaderboard" -Method Get
$leaderboard.leaderboard | Format-Table issue_id, overall_score, is_active

# View detailed metrics
$leaderboard.leaderboard | Select-Object -First 5 | ForEach-Object {
    [PSCustomObject]@{
        ID = $_.issue_id
        Score = $_.overall_score
        Severity = $_.dimension_scores.severity
        Impact = $_.dimension_scores.impact
        Scale = $_.dimension_scores.scale
        Recency = $_.dimension_scores.recency
    }
} | Format-Table

# Save to JSON file
$leaderboard | ConvertTo-Json -Depth 10 | Out-File "leaderboard.json"

##List ISSUES
# List all issues
$issues = Invoke-RestMethod -Uri "https://agent-issue-tracking.onrender.com/api/issues" -Method Get
$issues.issues | Format-Table issue_id, title, created_at

# Count issues
"Total issues: $($issues.issues.Count)"

##GET EVENTS

## GET DISCOVERY DATA

# Get insights across all discovery runs
$insights = Invoke-RestMethod -Uri "https://agent-issue-tracking.onrender.com/api/discovery/insights" -Method Get
$insights.insights | Format-List

# View key metrics
$i = $insights.insights
Write-Host "Total Reports: $($i.total_reports)" -ForegroundColor Green
Write-Host "Total Issues Created: $($i.total_issues_created)" -ForegroundColor Green
Write-Host "Average Issues/Run: $($i.average_issues_per_run)" -ForegroundColor Yellow