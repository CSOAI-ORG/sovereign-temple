# MEOKCLAW × Siri — Voice Control Setup

> **"Hey Siri, ask MEOKCLAW what's the weather in Paris"**
> 
> **"Hey Siri, ask SOV3 for status"**
>
> **"Hey Siri, run MEOKCLAW council on quantum computing"**

---

## 📱 What You Can Say

| Voice Command | What Happens |
|---|---|
| "Hey Siri, ask MEOKCLAW [question]" | Routes through dual-brain, Siri reads answer |
| "Hey Siri, ask MEOKCLAW fast [question]" | Uses fast/cheap hemisphere |
| "Hey Siri, run MEOKCLAW council on [topic]" | Runs 3 models, reads consensus |
| "Hey Siri, ask SOV3 for status" | Reads SOV3 agent dashboard |
| "Hey Siri, ask SOV3 how many agents" | Active agent count |
| "Hey Siri, delegate [task] to SOV3" | Submits task to agent swarm |
| "Hey Siri, ask MEOKCLAW how much I saved" | Cost savings summary |
| "Hey Siri, ask MEOKCLAW for help" | Lists available commands |

---

## 🔧 Setup (5 Minutes)

### Step 1: Get Your API Endpoint

Make sure your MEOKCLAW API is accessible. Options:
- **Local:** `http://localhost:3201` (same WiFi)
- **Ngrok:** `https://your-ngrok-url.ngrok.io` (anywhere)
- **Cloudflare Tunnel:** `https://meokclaw.yourdomain.com` (production)

### Step 2: Create the "Ask MEOKCLAW" Shortcut

1. Open **Shortcuts** app on iPhone
2. Tap **+** to create new shortcut
3. Tap **Add Action**
4. Search for **"Get contents of URL"**
5. Configure:
   - **URL:** `http://YOUR_API:3201/siri/chat?message=[URL-encoded-question]&mode=auto`
   - **Method:** GET
   - **Headers:** None needed (or add `Authorization: Bearer YOUR_KEY` if using enterprise auth)
6. Add **"Get Text from Input"** (extracts the plain text response)
7. Add **"Speak Text"**
8. Name the shortcut: **"Ask MEOKCLAW"**
9. Done ✅

### Step 3: Enable Siri

1. In Shortcuts, tap the **...** menu on your shortcut
2. Tap **"Add to Siri"** or **" Siri Phrase"**
3. Record: **"Ask MEOKCLAW"**
4. Tap **Done**

---

## 🎙️ Shortcut Configurations (Copy-Paste)

### Shortcut 1: Ask MEOKCLAW

```
Action: Get Contents of URL
URL: http://{{API_HOST}}/siri/chat?message=ShortcutInput&mode=auto
Method: GET

→ Get Text from Input
→ Speak Text
```

**Siri Phrase:** *"Ask MEOKCLAW"*

### Shortcut 2: MEOKCLAW Council

```
Action: Get Contents of URL
URL: http://{{API_HOST}}/siri/council?prompt=ShortcutInput&models=deepseek-v4-flash,deepseek-v4-pro
Method: GET

→ Get Text from Input
→ Speak Text
```

**Siri Phrase:** *"Run MEOKCLAW council"*

### Shortcut 3: SOV3 Status

```
Action: Get Contents of URL
URL: http://{{API_HOST}}/siri/sov3?command=status
Method: GET

→ Get Text from Input
→ Speak Text
```

**Siri Phrase:** *"Ask SOV3 for status"*

### Shortcut 4: SOV3 Delegate

```
Action: Get Contents of URL
URL: http://{{API_HOST}}/siri/sov3?command=delegate&task=ShortcutInput
Method: GET

→ Get Text from Input
→ Speak Text
```

**Siri Phrase:** *"Delegate to SOV3"*

### Shortcut 5: Cost Savings

```
Action: Get Contents of URL
URL: http://{{API_HOST}}/siri/chat?message=how+much+did+I+save
Method: GET

→ Get Text from Input
→ Speak Text
```

**Siri Phrase:** *"How much did MEOKCLAW save me"*

---

## 🔒 Security (Production)

For production use, add API key authentication:

1. In your shortcut, add a **Text** action with your API key
2. Add header: `Authorization: Bearer YOUR_API_KEY`
3. In the MEOKCLAW API, enable enterprise auth:
   ```bash
   curl -X POST http://localhost:3201/api/auth/keys \
     -d '{"name":"Siri","org_id":"YOUR_ORG","scopes":["chat:write"]}'
   ```

---

## 🌐 External Access (Ngrok / Cloudflare)

### Option A: Ngrok (Temporary)

```bash
ngrok http 3201
```

Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`) into your shortcuts.

### Option B: Cloudflare Tunnel (Permanent)

```bash
cloudflared tunnel --url http://localhost:3201
```

Or use a named tunnel with a custom domain.

---

## 🧪 Test Commands

After setup, try these:

```
"Hey Siri, ask MEOKCLAW what is 2 plus 2"
"Hey Siri, ask MEOKCLAW explain quantum computing simply"
"Hey Siri, run MEOKCLAW council on AI safety"
"Hey Siri, ask SOV3 for status"
"Hey Siri, delegate summarize yesterday's logs to SOV3"
"Hey Siri, ask MEOKCLAW how much I saved"
```

---

## 🏠 HomePod / CarPlay

These shortcuts work on:
- **iPhone** (obviously)
- **iPad**
- **HomePod** (via iPhone relay)
- **CarPlay** (while driving)
- **Apple Watch**
- **Mac** (macOS Shortcuts)

**CarPlay use case:** *"Hey Siri, ask MEOKCLAW to summarize my emails while I drive"*

---

## 🛠️ Troubleshooting

| Problem | Fix |
|---|---|
| "Shortcut not found" | Make sure Siri phrase is recorded clearly |
| "Could not connect" | Check API is reachable from phone (same WiFi or use ngrok) |
| "No response" | API might be busy; try `mode=fast` |
| "Text too long" | Siri truncates; use `mode=fast` for shorter answers |
| "Unauthorized" | Add API key header in shortcut |

---

## 🚀 Pro Tips

1. **Create a Siri Shortcut folder** called "MEOKCLAW" to organize
2. **Use Focus modes** to enable MEOKCLAW shortcuts only during work hours
3. **Combine with automations:** "When I arrive at office, ask SOV3 for status"
4. **Widget on home screen:** Add shortcut widget for one-tap access

---

## 📲 Download Shortcut (iCloud Link)

When deployed, create a shareable iCloud link:

```
Shortcuts app → Your Shortcut → Share → Copy iCloud Link
```

Share this link with your team. They tap it, and the shortcut installs automatically.

---

*Setup time: 5 minutes  
*Voice control: Priceless*
