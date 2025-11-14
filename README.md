# Proactive Monitoring Agent

A Creative agent continuously peppers questions to Vanna agent which continuously executes them. An Alert agent notifies the user via WhatsApp if something looks off.

## Overview

This system proactively monitors your database through three autonomous agents:

1. **Creative Agent** - Generates exploratory questions based on your schema, plus runs scheduled structured tasks
2. **Vanna Agent** - Converts questions to SQL and executes them against your database
3. **Alert Agent** - Analyzes results for anomalies and sends WhatsApp notifications when issues are detected

## Architecture

```
Creative Agent → Queue → Vanna Agent → Alert Agent → WhatsApp
├─ Exploratory         ├─ SQL Gen      ├─ Automatic
└─ Structured          └─ Execution    └─ Anomaly Detection
```

**Key Features:**
- Creative agent continuously generates relevant questions about your data
- Queue system prevents overwhelming the Vanna agent (max 10 items)
- Exploratory questions pause when queue is full
- Structured tasks always run on schedule
- Per-task alert configuration with intelligent anomaly detection
- WhatsApp notifications keep you informed

---

## Quick Start

### 1. Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env and add your API keys:
#   - OPENAI_API_KEY (required)
#   - VANNA_API_KEY (required)
#   - VANNA_USER_EMAIL (required)
#   - VANNA_AGENT_ID (required)

# Create schema.json (choose ONE option):

# OPTION A: Extract from BigQuery
gcloud auth application-default login
python extract_schema.py

# OPTION B: Convert from CSV
# 1. Create a CSV file describing your schema (see schema.example.csv)
# 2. Convert it to schema.json:
python csv_to_schema.py your_schema.csv --project your-project --dataset your-dataset

# OPTION C: Create manually
# Use schema.example.json as a template and customize for your database

# Create training_data.csv
# Use training_data.example.csv as a template with example question-SQL pairs
cp training_data.example.csv training_data.csv
# Edit with your own question-SQL examples
```

### 2. Configure Tasks

Create your tasks configuration:
```bash
cp tasks.example.yaml tasks.yaml
# Edit tasks.yaml with your monitoring tasks and questions
```

The example includes:
- Daily user engagement monitoring
- Revenue tracking with dropoff alerts
- Hourly order volume checks
- Weekly signup comparisons

### 3. Run

```bash
python main.py
```

---

## WhatsApp Alerts Setup

### Quick Start (Sandbox - Free Testing)

**1. Get Twilio Account**
- Sign up at https://www.twilio.com/try-twilio
- Get free trial credits ($15)

**2. Join WhatsApp Sandbox**
- Go to Console → Messaging → Try it out → Send a WhatsApp message
- Send "join <code>" to the Twilio WhatsApp number
- Note your credentials:
  - Account SID
  - Auth Token  
  - Sandbox Number (e.g., +14155238886)

**3. Configure Environment Variables**
Edit your `.env` file and add:
```bash
TWILIO_ENABLED=true
TWILIO_ACCOUNT_SID=your-account-sid
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886  # Sandbox number
TWILIO_WHATSAPP_TO=whatsapp:+12345678900    # YOUR number with country code
```

**4. Install Twilio** (already in requirements.txt)
```bash
pip install -r requirements.txt
```

**5. Test**
When alerts trigger, you'll receive WhatsApp messages! 📱

### WhatsApp Message Format
```
🔔 MONITORING ALERT

Task: USER_ENGAGEMENT
Type: structured

🚨 ANOMALY DETECTED (HIGH): Engagement dropped 15%

Question: What is user engagement...

Time: 2025-11-13 10:30:45
```

### Production Setup
For production without "sandbox" branding:
- Apply for WhatsApp Business API
- Get business verification (~1-2 weeks)
- Use approved business number

### Pricing
- **Sandbox:** FREE with trial credits
- **Production:** ~$0.005 per message
  - 10 alerts/day = $1.50/month
  - 100 alerts/day = $15/month

### Disable WhatsApp
Don't set `TWILIO_ENABLED` or set to `"false"` - alerts will only show in terminal.

---

## Configuration

### Task Configuration (`tasks.yaml`)

```yaml
structured_tasks:
  - name: vip_user_usage
    cadence_hours: 24  # Run daily
    question: "What is usage for adi@vanna.ai, aditya.sudhakar@gmail.com, and adi@theslyllama.com?"
    alert_mode: "anomaly"  # or "automatic"
    anomaly_threshold:
      type: "percent_change"
      value: 0.10  # 10% threshold
    
  - name: weekly_revenue
    cadence_hours: 168  # Run weekly (7 days)
    question: "What was revenue this week vs last week?"
    alert_mode: "automatic"

creative_agent:
  enabled: true
  cadence_hours: 1  # Run hourly
  alert_mode: "anomaly"
  anomaly_threshold:
    type: "general"
    value: 0.05  # 5% threshold
```

### Alert Modes

**`automatic`**
- Always alerts with results
- Use for: Critical metrics you always want to see
- Example: Daily revenue reports

**`anomaly`**
- Only alerts if anomaly detected
- Uses AI to analyze results against thresholds
- Use for: Monitoring that should be quiet unless something's wrong
- Example: VIP user activity (alert if drops >10%)

### Threshold Types

| Type | Description | Example |
|------|-------------|---------|
| `percent_change` | Detects % changes in either direction | Alert if 10% change |
| `dropoff` | Detects decreases only | Alert if drops 5% or more |
| `spike` | Detects increases only | Alert if increases 20% or more |
| `general` | AI decides what's anomalous | Baseline 5% threshold |

### Time Intervals

| Hours | Equivalent | Use Case |
|-------|-----------|----------|
| 1 | Hourly | Frequent checks |
| 24 | Daily | Standard monitoring |
| 168 | Weekly | Summary reports |
| 0.0014 | ~5 seconds | Testing only |
| 0.0028 | ~10 seconds | Testing only |

---

## Output Examples

### Normal Result (No Alert)
```
============================================================
✅ VANNA RESULT [STRUCTURED: vip_user_usage]
Question: What is usage for adi@vanna.ai...
Result:
Usage is 45 queries this week, up 7% from last week...
============================================================
```

### Automatic Alert
```
🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔
📢 ALERT: WEEKLY_REVENUE
Type: structured
Reason: Automatic alert (always notifies)
Question: What was revenue this week vs last week?
Timestamp: 2025-11-11 22:30:15
🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔
```

### Anomaly Alert
```
🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔
📢 ALERT: VIP_USER_USAGE
Type: structured
Reason: 🚨 ANOMALY DETECTED (HIGH): Usage dropped 15% week-over-week, exceeding 10% threshold
Question: What is usage for adi@vanna.ai...
Timestamp: 2025-11-11 22:30:15
🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔
```

---

## Managing Tasks

### Add a Task
Edit `tasks.yaml`:
```yaml
structured_tasks:
  - name: new_metric
    cadence_hours: 24
    question: "Your question here"
    alert_mode: "anomaly"
    anomaly_threshold:
      type: "percent_change"
      value: 0.10
```

### Modify a Task
Just edit the YAML and restart the agent (Ctrl+C, then re-run).

### Delete a Task
Remove the task from YAML and restart.

### Disable Creative Agent
```yaml
creative_agent:
  enabled: false
```

---

## Project Structure

```
proactive-agent/
├── main.py                      # Main monitoring agent (Creative/Vanna/Alert)
├── extract_schema.py            # BigQuery schema extractor
├── csv_to_schema.py             # CSV to schema.json converter
├── .env                         # Your secrets (not in git)
├── .env.example                 # Template for environment variables
├── tasks.yaml                   # Your monitoring tasks (create from example)
├── tasks.example.yaml           # Example tasks configuration
├── schema.json                  # Your database schema (create from examples)
├── schema.example.json          # Example schema (JSON format)
├── schema.example.csv           # Example schema (CSV format)
├── training_data.csv            # Your Q-SQL training pairs (create from example)
├── training_data.example.csv    # Example training data
├── questions.db                 # SQLite database (generated)
├── requirements.txt             # Python dependencies
├── setup_check.py               # Setup verification script
├── .gitignore                   # Excludes secrets and user files
└── README.md                    # This file
```

---

## How It Works

### 1. Creative Agent (Question Generation)

**Exploratory Questions:**
- AI generates novel questions based on your database schema and past Q-SQL pairs
- Checks for duplicates to avoid repetition
- Pauses if queue is full (>10 items) to prevent overwhelming Vanna

**Structured Tasks:**
- Runs predefined questions from `tasks.yaml` on a schedule
- Always executes on time
- Waits in queue if Vanna agent is busy

### 2. Vanna Agent (SQL Execution)

- Receives questions from the queue
- Converts natural language to SQL queries
- Executes against your database
- Returns results as text

### 3. Alert Agent (Anomaly Detection)

**Automatic Mode:**
- Every result triggers a WhatsApp alert
- No analysis needed
- Use for critical metrics you always want to see

**Anomaly Mode:**
- AI (GPT-4o-mini) analyzes results against configured thresholds
- Detects percent changes, dropoffs, spikes, and other anomalies
- Only sends WhatsApp alert if something looks off
- Keeps notifications relevant and actionable

---

## Troubleshooting

### Queue is full
```
⏭️  [EXPLORATORY] Queue full (11 items), skipping...
```
**Solution:** This is normal. Creative agent pauses exploratory questions until Vanna agent clears the queue.

### Vanna API error
```
❌ Vanna API error: ...
```
**Solution:** Check VANNA_API_KEY is set correctly.

### No schema.json
```
❌ schema.json not found!
```
**Solution:** Run `python extract_schema.py` first.

### OpenAI rate limit
**Solution:** Increase `cadence_hours` for the creative agent in `tasks.yaml`.

### WhatsApp alert failed
```
⚠️  WhatsApp alert failed: ...
```
**Solutions:**
- Verify you joined Twilio sandbox (send "join <code>")
- Check phone number format: `whatsapp:+1234567890` (include country code)
- Verify credentials are correct
- Check Twilio account has credits

### Twilio library not installed
```bash
pip install twilio
```

---

## Testing

### Quick Test (5-10 second intervals)
```bash
cp tasks_test.yaml tasks.yaml
python main.py
```

Watch for:
- Questions being generated
- Vanna API calls
- Results being displayed
- Alerts appearing (automatic and anomaly)

Press Ctrl+C to stop gracefully.

### Verification Checklist
- [ ] Schema extracted (`schema.json` exists)
- [ ] Training data present (`training_data.csv` exists)
- [ ] API keys set (OpenAI, Vanna)
- [ ] Tasks configured (`tasks.yaml`)
- [ ] Agent starts without errors
- [ ] Questions being generated
- [ ] Vanna responses received
- [ ] Alerts appearing correctly

---

## Next Steps

### Current Status
- ✅ Question generation (exploratory + structured)
- ✅ Vanna execution (SQL + results)
- ✅ Alert agent (automatic + anomaly detection)
- ✅ WhatsApp alerts (via Twilio)
- ✅ Terminal output

### Future Enhancements
- 🔜 Hot-reload tasks.yaml without restart
- 🔜 Dashboard for viewing history
- 🔜 Store results in database
- 🔜 Email alerts
- 🔜 Slack integration
- 🔜 Alert routing rules

---

## Support

### Verify Setup
```bash
python setup_check.py
```

### View Generated Questions
```bash
sqlite3 questions.db "SELECT * FROM generated_questions ORDER BY timestamp DESC LIMIT 10;"
```

### Export Questions to CSV
```bash
sqlite3 -header -csv questions.db "SELECT * FROM generated_questions;" > generated_questions.csv
```

---

## Contributing

To add new features:
1. Edit `main.py` for agent logic
2. Edit `tasks.yaml` for configuration
3. Update this README
4. Test with `tasks_test.yaml` first

---

## License

Internal use only.
