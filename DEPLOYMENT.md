# Deploying to Render

This guide will help you deploy the Curiosity Agent to Render for 24/7 monitoring.

## Prerequisites

1. GitHub account with this repository
2. Render account (sign up at https://render.com)
3. Your API keys and credentials ready:
   - OpenAI API key
   - Vanna API key, user email, and agent ID
   - Twilio credentials (if using WhatsApp alerts)

## Step 1: Prepare Your Files

Before deploying, you need to upload your private files to Render:

### Required Files
1. **tasks.yaml** - Your monitoring tasks configuration
2. **schema.json** - Your database schema
3. **training_data.csv** - Your SQL training examples

These files are in `.gitignore` (they contain private data), so you'll need to upload them manually after deployment.

## Step 2: Deploy to Render

**Note**: Render's free tier doesn't support background workers, so we'll deploy as a Web Service.

1. Go to https://dashboard.render.com
2. Click **New +** → **Web Service**
3. Connect your GitHub repository: `vanna-ai/proactive-agent`
4. Configure:
   - **Name**: `curiosity-agent`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`
   - **Plan**: `Free`
5. Click **Create Web Service**

**Important**: The deployment will initially fail because the required files (tasks.yaml, schema.json, training_data.csv) are missing. This is expected - we'll upload them in Step 4.

## Step 3: Set Environment Variables

In the Render dashboard, go to your service → **Environment** and add these variables:

```
OPENAI_API_KEY=your-openai-api-key
VANNA_API_KEY=your-vanna-api-key
VANNA_USER_EMAIL=your-vanna-email
VANNA_AGENT_ID=your-vanna-agent-id
VANNA_STRUCTURED_PREFIX=hosted app
VANNA_EXPLORATORY_PREFIX=hosted app
TWILIO_ENABLED=true
TWILIO_ACCOUNT_SID=your-twilio-sid
TWILIO_AUTH_TOKEN=your-twilio-token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
TWILIO_WHATSAPP_TO=whatsapp:+1234567890
```

**Note**: Replace all `your-*` values with your actual credentials.

## Step 4: Upload Private Files

After the service is deployed:

1. Go to your service in Render dashboard
2. Click **Shell** tab (opens a terminal to your running service)
3. Upload your files using one of these methods:

### Method A: Using Render Shell
```bash
# Create the files in the shell
cat > tasks.yaml << 'EOF'
[paste your tasks.yaml content here]
EOF

cat > schema.json << 'EOF'
[paste your schema.json content here]
EOF

cat > training_data.csv << 'EOF'
[paste your training_data.csv content here]
EOF
```

### Method B: Use Render Disk (Persistent Storage)
1. In your service settings, add a **Disk**
2. Mount point: `/data`
3. Update your code to read files from `/data` instead of root directory
4. Upload files via Render's file browser

## Step 5: Verify Deployment

1. Check the **Logs** tab in Render dashboard
2. You should see:
   ```
   ✅ Twilio WhatsApp enabled
   🚀 Starting Monitoring Agent...
   ✅ Database initialized
   📋 Structured tasks loaded: X
   ```
3. Wait for your scheduled tasks to run and verify WhatsApp alerts

## Updating tasks.yaml After Deployment

To update your monitoring tasks:

1. Go to Render dashboard → your service → **Shell**
2. Edit the file:
   ```bash
   nano tasks.yaml
   ```
3. Make your changes, save (Ctrl+O, Enter, Ctrl+X)
4. The agent will pick up changes on the next cycle
5. Or restart the service: Render dashboard → **Manual Deploy** → **Deploy latest commit**

## Important Notes

- **Free Tier Limits**: Render's free tier may spin down after 15 minutes of inactivity
- **Persistent Storage**: Free tier doesn't include persistent disks - files may be lost on restart
- **Upgrading**: Consider upgrading to a paid plan ($7/month) for:
  - Always-on service
  - Persistent disk storage
  - Better performance

## Troubleshooting

### Service keeps restarting
- Check logs for errors
- Verify all environment variables are set correctly
- Ensure files (tasks.yaml, schema.json, training_data.csv) exist

### No WhatsApp alerts
- Check TWILIO_ENABLED is set to "true"
- Verify Twilio credentials
- Check logs for WhatsApp send errors

### Database errors
- Ensure schema.json is uploaded and valid JSON
- Check training_data.csv format

## Alternative: Render Disk for Persistence

To ensure files persist across deployments:

1. Add to `render.yaml`:
   ```yaml
   disk:
     name: data
     mountPath: /data
     sizeGB: 1
   ```
2. Update main.py to read files from `/data/`:
   - `/data/tasks.yaml`
   - `/data/schema.json`
   - `/data/training_data.csv`
   - `/data/questions.db`
