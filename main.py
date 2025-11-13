"""
Main Monitoring Agent: Runs both exploratory and structured monitoring
- Exploratory: AI-generated questions based on schema
- Structured: Predefined tasks from tasks.yaml
- Both execute via Vanna and check for anomalies
"""

import schedule
import time
import json
import sqlite3
import pandas as pd
from openai import OpenAI
from datetime import datetime
import os
import yaml
import requests
from queue import Queue
from threading import Thread

# Initialize OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Vanna configuration
VANNA_API_KEY = os.environ.get("VANNA_API_KEY", "vn-96862437e7034ebeb1082c45e0181caf")
VANNA_API_URL = "https://app.vanna.ai/api/v2/chat_sse"
VANNA_USER_EMAIL = os.environ.get("VANNA_USER_EMAIL", "adi@vanna.ai")
VANNA_AGENT_ID = os.environ.get("VANNA_AGENT_ID", "hosted-app-usage")
VANNA_STRUCTURED_PREFIX = os.environ.get("VANNA_STRUCTURED_PREFIX", "hosted app")  # For structured tasks
VANNA_EXPLORATORY_PREFIX = os.environ.get("VANNA_EXPLORATORY_PREFIX", "hosted app")  # For exploratory questions

# Twilio WhatsApp configuration
TWILIO_ENABLED = os.environ.get("TWILIO_ENABLED", "false").lower() == "true"
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_FROM = os.environ.get("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")  # Twilio sandbox
TWILIO_WHATSAPP_TO = os.environ.get("TWILIO_WHATSAPP_TO")  # Your WhatsApp number (format: whatsapp:+1234567890)

# Initialize Twilio client if enabled
twilio_client = None
if TWILIO_ENABLED:
    try:
        from twilio.rest import Client
        twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        print("✅ Twilio WhatsApp enabled")
    except ImportError:
        print("⚠️  Twilio library not installed. Run: pip install twilio")
        TWILIO_ENABLED = False
    except Exception as e:
        print(f"⚠️  Twilio configuration error: {e}")
        TWILIO_ENABLED = False

# Question queue for Vanna processing
question_queue = Queue()

# Database setup
DB_FILE = "questions.db"

def init_db():
    """Initialize SQLite database for storing questions"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS generated_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT UNIQUE NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    print("✅ Database initialized")


def load_schema():
    """Load the BigQuery schema"""
    with open("schema.json", "r") as f:
        return json.load(f)


def load_training_pairs():
    """Load existing Q-SQL training pairs"""
    df = pd.read_csv("training_data.csv")
    # Get just questions and SQL for context
    pairs = df[['question', 'sql']].head(20)  # Use first 20 as examples
    return pairs.to_dict('records')


def load_tasks():
    """Load monitoring tasks from YAML config"""
    try:
        with open("tasks.yaml", "r") as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        print("⚠️  tasks.yaml not found, running in curiosity-only mode")
        return {"structured_tasks": [], "curiosity": {"enabled": True, "cadence_seconds": 2}}


def call_vanna(question, task_name="unknown", task_type="exploratory"):
    """Execute question via Vanna API"""
    try:
        # Use different prefix based on task type
        if task_type == "exploratory":
            prefix = VANNA_EXPLORATORY_PREFIX
        else:
            prefix = VANNA_STRUCTURED_PREFIX
        
        prefixed_question = f"{prefix}: {question}"
        
        payload = {
            "message": prefixed_question,
            "user_email": VANNA_USER_EMAIL,
            "agent_id": VANNA_AGENT_ID,
            "acceptable_responses": ["text", "dataframe"]
        }
        
        headers = {
            "Content-Type": "application/json",
            "VANNA-API-KEY": VANNA_API_KEY
        }
        
        print(f"   🔍 Calling Vanna API...")
        
        response = requests.post(VANNA_API_URL, json=payload, headers=headers, stream=True)
        
        # Parse SSE response
        result_text = ""
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    data_str = line_str[6:]  # Remove 'data: ' prefix
                    try:
                        data = json.loads(data_str)
                        if 'text' in data:
                            result_text += data['text']
                    except json.JSONDecodeError:
                        continue
        
        return {
            "question": question,
            "task_name": task_name,
            "task_type": task_type,
            "result": result_text,
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        print(f"   ❌ Vanna API error: {e}")
        return None


def detect_anomaly(result_text, threshold_config):
    """
    Detect anomalies in Vanna results using LLM
    Returns: {"anomaly_detected": bool, "reason": str, "severity": str}
    """
    try:
        prompt = f"""Analyze this data query result for anomalies.

Result: {result_text}

Anomaly Detection Rules:
- Threshold Type: {threshold_config.get('type', 'general')}
- Threshold Value: {threshold_config.get('value', 0.05) * 100}%

Look for:
- Significant percentage changes (above threshold)
- Unusual spikes or drops
- Concerning trends
- Data quality issues

Respond in JSON format:
{{
    "anomaly_detected": true/false,
    "reason": "brief explanation of what's anomalous",
    "severity": "low/medium/high",
    "alert_message": "clear, actionable message for the user"
}}

If no anomaly detected, set anomaly_detected to false and leave other fields empty."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an anomaly detection analyst. Analyze data and identify issues."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.3  # Lower temperature for consistent analysis
        )
        
        result = response.choices[0].message.content.strip()
        # Clean up markdown if present
        result = result.replace('```json', '').replace('```', '').strip()
        
        return json.loads(result)
        
    except Exception as e:
        print(f"   ⚠️  Anomaly detection error: {e}")
        return {"anomaly_detected": False, "reason": "Error in detection", "severity": "low"}


def send_whatsapp_alert(task_name, task_type, alert_reason, question):
    """Send alert via WhatsApp using Twilio"""
    if not TWILIO_ENABLED or not twilio_client:
        return False
    
    try:
        # Format message
        message = f"""🔔 MONITORING ALERT

Task: {task_name.upper()}
Type: {task_type}

{alert_reason}

Question: {question}

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

        # Send via Twilio
        twilio_client.messages.create(
            body=message,
            from_=TWILIO_WHATSAPP_FROM,
            to=TWILIO_WHATSAPP_TO
        )
        
        print(f"   📱 WhatsApp alert sent!")
        return True
        
    except Exception as e:
        print(f"   ⚠️  WhatsApp alert failed: {e}")
        return False


def get_recent_questions(limit=10):
    """Get recently generated questions from database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT question, timestamp 
        FROM generated_questions 
        ORDER BY timestamp DESC 
        LIMIT ?
    """, (limit,))
    questions = cursor.fetchall()
    conn.close()
    return [q[0] for q in questions]


def question_exists(question):
    """Check if question already exists in database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM generated_questions WHERE question = ?", (question,))
    exists = cursor.fetchone()[0] > 0
    conn.close()
    return exists


def save_question(question):
    """Save generated question to database"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO generated_questions (question) VALUES (?)", (question,))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        # Question already exists
        return False


def build_prompt(schema, training_pairs, recent_questions):
    """Build the prompt for question generation"""
    
    # Format schema info concisely
    schema_summary = f"Dataset: {schema['dataset_id']}\n\nTables:\n"
    for table in schema['tables']:
        columns = ", ".join([f"{col['name']} ({col['type']})" for col in table['columns']])
        schema_summary += f"- {table['table_name']}: {columns}\n"
    
    # Format training examples
    examples_text = "Example questions from training data:\n"
    for i, pair in enumerate(training_pairs[:5], 1):
        examples_text += f"{i}. {pair['question']}\n"
    
    # Format recent questions
    recent_text = ""
    if recent_questions:
        recent_text = "\n\nRecently generated questions (DON'T repeat these):\n"
        for i, q in enumerate(recent_questions, 1):
            recent_text += f"{i}. {q}\n"
    
    prompt = f"""You are a curious data analyst exploring an e-commerce database. Generate ONE specific, measurable question that would be insightful to ask.

{schema_summary}

{examples_text}
{recent_text}

Guidelines:
- Generate questions similar in style to the training examples
- Focus on business metrics: sales, users, products, orders, inventory
- Include time comparisons (today vs yesterday, this week vs last week, etc.)
- Ask about trends, top performers, anomalies
- Be specific and measurable
- DON'T repeat recent questions - create variations or explore new angles

Generate ONE question only, no explanation needed."""

    return prompt


def generate_question(schema, training_pairs, recent_questions):
    """Generate a new question using OpenAI"""
    
    prompt = build_prompt(schema, training_pairs, recent_questions)
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a data analyst generating insightful database questions."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
            temperature=0.8  # Higher temperature for more variety
        )
        
        question = response.choices[0].message.content.strip()
        
        # Remove quotes if present
        question = question.strip('"\'')
        
        return question
        
    except Exception as e:
        print(f"❌ Error generating question: {e}")
        return None


def vanna_worker():
    """Background worker that processes questions from the queue via Vanna"""
    print("🔧 Vanna worker started")
    
    while True:
        # Get next question from queue (blocks until available)
        queue_item = question_queue.get()
        
        question = queue_item['question']
        task_name = queue_item['task_name']
        task_type = queue_item['task_type']
        alert_mode = queue_item.get('alert_mode', 'anomaly')
        threshold = queue_item.get('threshold', {'type': 'general', 'value': 0.05})
        
        # Call Vanna
        result = call_vanna(question, task_name, task_type)
        
        if result:
            # Print full result
            print(f"\n{'='*60}")
            print(f"✅ VANNA RESULT [{task_type.upper()}: {task_name}]")
            print(f"Question: {question}")
            print(f"Result:\n{result['result']}")
            print(f"{'='*60}\n")
            
            # Alert Agent: Decide whether to alert
            should_alert = False
            alert_reason = ""
            
            if alert_mode == "automatic":
                # Always alert
                should_alert = True
                alert_reason = "Automatic alert (always notifies)"
            elif alert_mode == "anomaly":
                # Check for anomalies
                anomaly = detect_anomaly(result['result'], threshold)
                if anomaly.get('anomaly_detected'):
                    should_alert = True
                    alert_reason = f"🚨 ANOMALY DETECTED ({anomaly.get('severity', 'unknown').upper()}): {anomaly.get('alert_message', anomaly.get('reason', 'Unknown anomaly'))}"
            
            # Send alert if needed
            if should_alert:
                print(f"\n{'🔔'*30}")
                print(f"📢 ALERT: {task_name.upper()}")
                print(f"Type: {task_type}")
                print(f"Reason: {alert_reason}")
                print(f"Question: {question}")
                print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"{'🔔'*30}\n")
                
                # Send WhatsApp alert
                send_whatsapp_alert(task_name, task_type, alert_reason, question)
        
        # Mark task as done
        question_queue.task_done()


def question_generation_cycle():
    """Main cycle: generate and add question to Vanna queue"""
    
    # Check queue size - don't overwhelm
    if question_queue.qsize() > 10:
        print(f"⏭️  [EXPLORATORY] Queue full ({question_queue.qsize()} items), skipping...")
        return
    
    # Load context
    schema = load_schema()
    training_pairs = load_training_pairs()
    recent_questions = get_recent_questions(limit=10)
    
    # Generate question
    question = generate_question(schema, training_pairs, recent_questions)
    
    if not question:
        return
    
    # Check if it's a duplicate
    if question_exists(question):
        print(f"⏭️  [EXPLORATORY] Skipping duplicate: {question}")
        return
    
    # Save to database
    if save_question(question):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"🤔 [EXPLORATORY {timestamp}] {VANNA_EXPLORATORY_PREFIX}: {question}")
        
        # Get curiosity config for alert settings
        config = load_tasks()
        curiosity_config = config.get('curiosity', {})
        
        # Add to Vanna queue with alert settings
        question_queue.put({
            'question': question,
            'task_name': 'exploratory',
            'task_type': 'exploratory',
            'alert_mode': curiosity_config.get('alert_mode', 'anomaly'),
            'threshold': curiosity_config.get('anomaly_threshold', {'type': 'general', 'value': 0.05})
        })
    else:
        print(f"⏭️  [EXPLORATORY] Question already exists")


def run_structured_task(task):
    """Execute a structured monitoring task"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    task_name = task['name']
    question = task['question']
    
    print(f"📋 [STRUCTURED: {task_name.upper()} {timestamp}] {VANNA_STRUCTURED_PREFIX}: {question}")
    
    # Add to Vanna queue with alert settings from task config
    question_queue.put({
        'question': question,
        'task_name': task_name,
        'task_type': 'structured',
        'alert_mode': task.get('alert_mode', 'anomaly'),
        'threshold': task.get('anomaly_threshold', {'type': 'general', 'value': 0.05})
    })


def main():
    """Main entry point"""
    
    print("🚀 Starting Monitoring Agent...")
    print("="*60)
    
    # Check required files
    if not os.path.exists("schema.json"):
        print("❌ schema.json not found! Run extract_schema.py first.")
        return
    
    if not os.path.exists("training_data.csv"):
        print("❌ Training data CSV not found!")
        return
    
    # Initialize database
    init_db()
    
    # Start Vanna worker thread
    vanna_thread = Thread(target=vanna_worker, daemon=True)
    vanna_thread.start()
    
    # Load tasks configuration
    config = load_tasks()
    structured_tasks = config.get('structured_tasks', [])
    curiosity_config = config.get('curiosity', {'enabled': True, 'cadence_seconds': 2})
    
    # Get initial count
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM generated_questions")
    initial_count = cursor.fetchone()[0]
    conn.close()
    
    print(f"📊 Questions in database: {initial_count}")
    print(f"📋 Structured tasks loaded: {len(structured_tasks)}")
    print(f"🤔 Exploratory mode: {'enabled' if curiosity_config.get('enabled') else 'disabled'}")
    print(f"🔧 Vanna worker: running")
    print("="*60)
    
    # Schedule structured tasks
    if structured_tasks:
        print("\n📋 Scheduled Tasks:")
        for task in structured_tasks:
            cadence_hours = task.get('cadence_hours', 24)
            task_name = task['name']
            alert_mode = task.get('alert_mode', 'anomaly')
            
            # Display cadence in human-readable format
            if cadence_hours >= 168:
                display = f"{cadence_hours/168:.1f} weeks"
            elif cadence_hours >= 24:
                display = f"{cadence_hours/24:.1f} days"
            else:
                display = f"{cadence_hours} hours"
            
            print(f"   - {task_name}: every {display} (alert: {alert_mode})")
            schedule.every(cadence_hours).hours.do(run_structured_task, task)
    
    # Schedule curiosity agent
    if curiosity_config.get('enabled'):
        curiosity_cadence_hours = curiosity_config.get('cadence_hours', 1)
        alert_mode = curiosity_config.get('alert_mode', 'anomaly')
        
        if curiosity_cadence_hours >= 24:
            display = f"{curiosity_cadence_hours/24:.1f} days"
        else:
            display = f"{curiosity_cadence_hours} hours"
        
        print(f"\n🤔 Exploratory Agent: every {display} (alert: {alert_mode})")
        schedule.every(curiosity_cadence_hours).hours.do(question_generation_cycle)
    
    print("\n" + "="*60)
    print("Press Ctrl+C to stop\n")
    
    # Run all tasks once immediately
    for task in structured_tasks:
        run_structured_task(task)
    
    if curiosity_config.get('enabled'):
        question_generation_cycle()
    
    # Main loop
    try:
        while True:
            schedule.run_pending()
            time.sleep(0.5)  # Check more frequently for precise timing
    except KeyboardInterrupt:
        print("\n\n" + "="*60)
        print("🛑 Stopping Monitoring Agent...")
        
        # Wait for queue to finish
        print(f"⏳ Waiting for {question_queue.qsize()} remaining items in queue...")
        question_queue.join()
        
        # Final count
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM generated_questions")
        final_count = cursor.fetchone()[0]
        conn.close()
        
        print(f"📊 Exploratory questions generated this session: {final_count - initial_count}")
        print(f"📊 Total questions in database: {final_count}")
        print("="*60)


if __name__ == "__main__":
    main()
