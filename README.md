# Agentic AI-Based Website Traffic Anomaly Detection and Root Cause Analysis using Grafana and Prometheus

## 1. Project Overview

This project is a real-time **Agentic AI-based website traffic anomaly detection system**.

The system monitors website/backend metrics such as:

- Website status
- Response time
- Error rate
- Requests per minute
- Active users

The metrics are collected by **Prometheus**, analyzed by a local Python-based **agentic anomaly detection system**, and visualized in **Grafana**. Grafana also creates alerts when abnormal website behavior is detected.

No external AI API key is used. The agentic logic runs locally in Python.

---

## 2. Project Architecture

```text
Website Metrics Exporter
        ↓
Prometheus
        ↓
Agentic Anomaly Agent
        ↓
Prometheus
        ↓
Grafana Dashboard + Alerts
```

### Explanation

1. `website_metrics.py` generates or exposes website metrics.
2. Prometheus scrapes those metrics from `localhost:8000`.
3. `agentic_anomaly_agent.py` reads metrics from Prometheus.
4. The agent detects anomalies and generates root cause, severity, recommendation, and AI-style explanation.
5. The agent exports its own metrics on `localhost:8001`.
6. Prometheus scrapes the agent metrics.
7. Grafana visualizes everything and triggers alerts.

---

## 3. Agents Used in the Project

The Python agentic system contains 5 logical agents:

| Agent | Work |
|---|---|
| Metrics Collector Agent | Reads latest website metrics from Prometheus |
| Anomaly Detection Agent | Detects abnormal website behavior |
| Root Cause Analysis Agent | Finds the possible affected layer |
| Severity Classification Agent | Classifies the issue as medium, high, or critical |
| Recommendation Agent | Suggests the next action |

All agents run continuously in real time inside `agentic_anomaly_agent.py`.

---

## 4. Tools and Technologies Used

| Tool | Purpose |
|---|---|
| Python | To create website metrics exporter and agentic anomaly agent |
| Prometheus | To collect and store metrics |
| Grafana | To create dashboard and alerts |
| prometheus_client | Python library to expose metrics |
| requests | Python library to call Prometheus API |

---

## 5. Project Folder Setup

Create the project folder:

```bash
mkdir -p ~/Desktop/anomaly
cd ~/Desktop/anomaly
```

Create a Python virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install Python dependencies:

```bash
pip install prometheus_client requests
```

---

## 6. Create Website Metrics Exporter

Create the file:

```bash
nano website_metrics.py
```

Paste this code:

```python
from prometheus_client import start_http_server, Gauge
import random
import time

website_active_users = Gauge("website_active_users", "Number of active users on the website")
website_requests_per_minute = Gauge("website_requests_per_minute", "Website requests per minute")
website_response_time_ms = Gauge("website_response_time_ms", "Website response time in milliseconds")
website_error_rate_percent = Gauge("website_error_rate_percent", "Website error rate percentage")
website_up = Gauge("website_up", "Website status: 1 means up, 0 means down")

# Change this value to test different anomalies.
# Options:
# normal, backend_overload, high_response_time, high_error_rate, traffic_spike, website_down, random
TEST_MODE = "random"

print("Website Metrics Exporter")
print("Prometheus endpoint: http://localhost:8000/metrics")
print("Exporter started. Updating metrics every 5 seconds ...")

start_http_server(8000)

cycle = 0

while True:
    cycle += 1

    users = random.randint(50, 300)
    traffic = random.randint(200, 700)
    response = random.randint(100, 400)
    errors = random.uniform(0, 3)
    status = 1

    mode = TEST_MODE

    if TEST_MODE == "random":
        mode = random.choice([
            "normal",
            "normal",
            "normal",
            "traffic_spike",
            "high_response_time",
            "high_error_rate",
            "website_down",
            "backend_overload"
        ])

    if mode == "backend_overload":
        response = 1200
        errors = 10
        traffic = 900
        status = 1
        print(f"[Cycle {cycle}] ANOMALY: backend_overload")

    elif mode == "high_response_time":
        response = 1200
        errors = 2
        status = 1
        print(f"[Cycle {cycle}] ANOMALY: high_response_time")

    elif mode == "high_error_rate":
        response = 300
        errors = 12
        status = 1
        print(f"[Cycle {cycle}] ANOMALY: high_error_rate")

    elif mode == "traffic_spike":
        traffic = 1500
        response = 450
        errors = 2
        status = 1
        print(f"[Cycle {cycle}] ANOMALY: traffic_spike")

    elif mode == "website_down":
        traffic = 0
        response = 0
        errors = 100
        status = 0
        print(f"[Cycle {cycle}] ANOMALY: website_down")

    else:
        print(f"[Cycle {cycle}] Normal")

    website_active_users.set(users)
    website_requests_per_minute.set(traffic)
    website_response_time_ms.set(response)
    website_error_rate_percent.set(errors)
    website_up.set(status)

    time.sleep(5)
```

Save the file:

```text
Ctrl + O
Enter
Ctrl + X
```

Run it:

```bash
cd ~/Desktop/anomaly
source venv/bin/activate
python3 website_metrics.py
```

Test in browser:

```text
http://localhost:8000/metrics
```

Or test using terminal:

```bash
curl http://localhost:8000/metrics
```

---

## 7. Configure Prometheus

Open Prometheus config:

```bash
sudo nano /etc/prometheus/prometheus.yml
```

Add these scrape jobs inside `scrape_configs`:

```yaml
  - job_name: "website_metrics"
    static_configs:
      - targets: ["localhost:8000"]

  - job_name: "agentic_anomaly_agent"
    static_configs:
      - targets: ["localhost:8001"]
```

Save the file:

```text
Ctrl + O
Enter
Ctrl + X
```

Restart Prometheus:

```bash
sudo systemctl restart prometheus
```

Check Prometheus status:

```bash
sudo systemctl status prometheus
```

Open Prometheus:

```text
http://localhost:9090
```

Check target status:

```text
http://localhost:9090/targets
```

Both targets should be UP:

```text
website_metrics
agentic_anomaly_agent
```

Note: `agentic_anomaly_agent` will show UP only after running `agentic_anomaly_agent.py`.

---

## 8. Create Agentic Anomaly Agent

Create the file:

```bash
cd ~/Desktop/anomaly
nano agentic_anomaly_agent.py
```

Paste this code:

```python
from prometheus_client import start_http_server, Gauge, Counter
import requests
import time

PROMETHEUS_URL = "http://localhost:9090/api/v1/query"

agent_overall_anomaly = Gauge(
    "agent_overall_anomaly",
    "Overall anomaly status detected by the agent. 0 means normal, 1 means anomaly."
)

agent_anomaly_score = Gauge(
    "agent_anomaly_score",
    "Anomaly score generated by the agent."
)

agent_step_status = Gauge(
    "agent_step_status",
    "Status of each agent step.",
    ["agent", "step", "status"]
)

agent_anomaly_detail = Gauge(
    "agent_anomaly_detail",
    "Detailed anomaly result generated by the agent.",
    ["agent", "anomaly_type", "location", "severity", "recommendation", "action"]
)

agent_ai_answer = Gauge(
    "agent_ai_answer",
    "AI-style explanation generated by the local agentic system.",
    ["anomaly_type", "ai_answer", "reason", "next_action"]
)

agent_anomaly_events_total = Counter(
    "agent_anomaly_events_total",
    "Total anomaly events detected by the agent.",
    ["anomaly_type", "location", "severity"]
)

previous_anomaly_type = "normal"


def query_prometheus(metric_name):
    try:
        response = requests.get(
            PROMETHEUS_URL,
            params={"query": metric_name},
            timeout=5
        )
        data = response.json()

        if data["status"] == "success" and data["data"]["result"]:
            return float(data["data"]["result"][0]["value"][1])

        return 0.0

    except Exception as error:
        print("Prometheus query error:", error)
        return 0.0


def reset_agent_metrics():
    agent_step_status.clear()
    agent_anomaly_detail.clear()
    agent_ai_answer.clear()


def analyze_metrics(website_up, response_time, error_rate, traffic):
    if website_up < 1:
        return {
            "anomaly_type": "website_down",
            "location": "availability_layer",
            "severity": "critical",
            "recommendation": "check_website_service",
            "action": "restart_or_check_app",
            "score": 100,
            "reason": "The website status metric is 0, which means the website is down.",
            "ai_answer": "The agent detected that the website is down.",
            "next_action": "Restart or check the website service."
        }

    if response_time > 800 and error_rate > 5:
        return {
            "anomaly_type": "backend_overload",
            "location": "backend_overload",
            "severity": "critical",
            "recommendation": "scale_or_restart_backend",
            "action": "reduce_load_or_scale",
            "score": 95,
            "reason": "High response time and high error rate happened together.",
            "ai_answer": "The agent detected backend overload.",
            "next_action": "Scale or restart the backend service."
        }

    if response_time > 800:
        return {
            "anomaly_type": "high_response_time",
            "location": "backend_api_layer",
            "severity": "high",
            "recommendation": "check_backend_or_network",
            "action": "investigate_latency",
            "score": min(response_time / 10, 100),
            "reason": "The website response time crossed the safe threshold.",
            "ai_answer": "The agent detected high response time in the backend API layer.",
            "next_action": "Investigate backend latency and network delay."
        }

    if error_rate > 5:
        return {
            "anomaly_type": "high_error_rate",
            "location": "application_layer",
            "severity": "critical",
            "recommendation": "check_application_logs",
            "action": "debug_errors",
            "score": min(error_rate * 10, 100),
            "reason": "The website error rate crossed the safe threshold.",
            "ai_answer": "The agent detected a high error rate in the application layer.",
            "next_action": "Check application logs and debug errors."
        }

    if traffic > 1000:
        return {
            "anomaly_type": "traffic_spike",
            "location": "traffic_layer",
            "severity": "medium",
            "recommendation": "check_bot_or_unusual_traffic",
            "action": "inspect_traffic_source",
            "score": min(traffic / 20, 100),
            "reason": "Requests per minute increased suddenly.",
            "ai_answer": "The agent detected a sudden traffic spike in the traffic layer.",
            "next_action": "Inspect traffic source and check for bots."
        }

    return {
        "anomaly_type": "normal",
        "location": "none",
        "severity": "none",
        "recommendation": "continue_monitoring",
        "action": "continue_monitoring",
        "score": 0,
        "reason": "All website metrics are within safe range.",
        "ai_answer": "All agents report normal website behavior. No anomaly is detected.",
        "next_action": "Continue monitoring."
    }


print("Agentic Anomaly Agent")
print("Agent metrics endpoint: http://localhost:8001/metrics")
print("Agent started. Checking Prometheus every 10 seconds ...")

start_http_server(8001)

while True:
    website_up = query_prometheus("website_up")
    response_time = query_prometheus("website_response_time_ms")
    error_rate = query_prometheus("website_error_rate_percent")
    traffic = query_prometheus("website_requests_per_minute")

    reset_agent_metrics()

    result = analyze_metrics(website_up, response_time, error_rate, traffic)

    anomaly_type = result["anomaly_type"]
    location = result["location"]
    severity = result["severity"]
    recommendation = result["recommendation"]
    action = result["action"]
    score = result["score"]
    reason = result["reason"]
    ai_answer = result["ai_answer"]
    next_action = result["next_action"]

    anomaly_found = 0 if anomaly_type == "normal" else 1

    agent_overall_anomaly.set(anomaly_found)
    agent_anomaly_score.set(score)

    agent_step_status.labels(
        agent="Metrics Collector Agent",
        step="collect_metrics",
        status="success"
    ).set(1)

    agent_step_status.labels(
        agent="Anomaly Detection Agent",
        step="detect_anomaly",
        status=anomaly_type
    ).set(1)

    agent_step_status.labels(
        agent="Root Cause Analysis Agent",
        step="find_root_cause",
        status=location
    ).set(1)

    agent_step_status.labels(
        agent="Severity Classification Agent",
        step="classify_severity",
        status=severity
    ).set(1)

    agent_step_status.labels(
        agent="Recommendation Agent",
        step="recommend_action",
        status=action
    ).set(1)

    agent_anomaly_detail.labels(
        agent="Anomaly Detection Agent",
        anomaly_type=anomaly_type,
        location=location,
        severity=severity,
        recommendation=recommendation,
        action=action
    ).set(1)

    agent_ai_answer.labels(
        anomaly_type=anomaly_type,
        ai_answer=ai_answer,
        reason=reason,
        next_action=next_action
    ).set(1)

    if anomaly_type != "normal" and anomaly_type != previous_anomaly_type:
        agent_anomaly_events_total.labels(
            anomaly_type=anomaly_type,
            location=location,
            severity=severity
        ).inc()

        print("Anomaly Count Updated:", anomaly_type)

    if anomaly_type == "normal":
        previous_anomaly_type = "normal"
    else:
        previous_anomaly_type = anomaly_type

    print(
        "Agent Decision:",
        anomaly_type,
        "| Score:",
        score,
        "| Severity:",
        severity,
        "| Action:",
        action
    )

    time.sleep(10)
```

Save the file:

```text
Ctrl + O
Enter
Ctrl + X
```

Run syntax check:

```bash
python3 -m py_compile agentic_anomaly_agent.py
```

If there is no output, the file is correct.

Run the agent:

```bash
cd ~/Desktop/anomaly
source venv/bin/activate
python3 agentic_anomaly_agent.py
```

Test agent metrics:

```bash
curl http://localhost:8001/metrics
```

Check only agent metrics:

```bash
curl -s http://localhost:8001/metrics | grep agent_
```

---

## 9. Important Local API Used

This project does not use OpenAI API or any paid AI API.

The local agent uses the Prometheus HTTP API:

```text
http://localhost:9090/api/v1/query
```

In code:

```python
PROMETHEUS_URL = "http://localhost:9090/api/v1/query"
```

This does not require an API key because Prometheus is running locally.

---

## 10. Run the Complete Project

Use 2 terminals.

### Terminal 1: Website Metrics Exporter

```bash
cd ~/Desktop/anomaly
source venv/bin/activate
python3 website_metrics.py
```

### Terminal 2: Agentic Anomaly Agent

```bash
cd ~/Desktop/anomaly
source venv/bin/activate
python3 agentic_anomaly_agent.py
```

Make sure Prometheus and Grafana are running:

```bash
sudo systemctl status prometheus
sudo systemctl status grafana-server
```

Open:

```text
Prometheus: http://localhost:9090
Grafana:    http://localhost:3000
```

---

## 11. Prometheus Queries to Test

Open Prometheus:

```text
http://localhost:9090
```

Test website metrics:

```promql
website_up
```

```promql
website_response_time_ms
```

```promql
website_error_rate_percent
```

```promql
website_requests_per_minute
```

Test agent metrics:

```promql
agent_overall_anomaly
```

```promql
agent_anomaly_score
```

```promql
agent_anomaly_detail == 1
```

```promql
agent_ai_answer == 1
```

```promql
agent_step_status == 1
```

---

## 12. Grafana Data Source Setup

Open Grafana:

```text
http://localhost:3000
```

Default login is usually:

```text
username: admin
password: admin
```

Go to:

```text
Connections → Data sources → Add data source → Prometheus
```

Set Prometheus URL:

```text
http://localhost:9090
```

Click:

```text
Save & test
```

---

## 13. Grafana Dashboard Panels

Create a dashboard:

```text
Dashboards → New dashboard → Add visualization
```

Use Prometheus as the data source.

### Website Panels

| Panel Title | Query | Visualization |
|---|---|---|
| Website Response Time | `website_response_time_ms` | Time series |
| Website Error Rate | `website_error_rate_percent` | Gauge |
| Website Requests Per Minute | `website_requests_per_minute` | Time series |
| Website Status | `website_up` | Stat |

### Agent Panels

| Panel Title | Query | Visualization |
|---|---|---|
| Agent Overall Anomaly Status | `agent_overall_anomaly` | Stat |
| Agent Anomaly Score | `agent_anomaly_score` | Gauge |
| Real-Time Agent Step Status | `agent_step_status == 1` | Table |
| Agent Root Cause Explanation | `agent_anomaly_detail == 1` | Table |
| AI Generated Answer | `agent_ai_answer == 1` | Table |
| Recent Anomaly Detected | `max_over_time(agent_overall_anomaly[5m]) or vector(0)` | Stat |
| Total Anomaly Count | `sum(agent_anomaly_events_total) or vector(0)` | Stat |
| Anomaly Count by Type | `sum by (anomaly_type) (agent_anomaly_events_total)` | Table or Bar chart |
| Anomaly Count by Severity | `sum by (severity) (agent_anomaly_events_total)` | Table or Bar chart |

For table panels, use:

```text
Query type: Instant
Format: Table
```

---

## 14. Alert Rules in Grafana

Go to:

```text
Alerting → Alert rules → New alert rule
```

Create these alerts.

### Main Alert

Alert name:

```text
Agentic Website Anomaly Detected
```

Query:

```promql
max(agent_overall_anomaly) or vector(0)
```

Condition:

```text
Is above 0
```

Pending period:

```text
30s or 1m
```

### Backend Overload Alert

```promql
max_over_time(agent_anomaly_detail{anomaly_type="backend_overload"}[5m]) or vector(0)
```

### Website Down Alert

```promql
max_over_time(agent_anomaly_detail{anomaly_type="website_down"}[5m]) or vector(0)
```

### High Response Time Alert

```promql
max_over_time(agent_anomaly_detail{anomaly_type="high_response_time"}[5m]) or vector(0)
```

### High Error Rate Alert

```promql
max_over_time(agent_anomaly_detail{anomaly_type="high_error_rate"}[5m]) or vector(0)
```

### Traffic Spike Alert

```promql
max_over_time(agent_anomaly_detail{anomaly_type="traffic_spike"}[5m]) or vector(0)
```

For all anomaly-specific alerts:

```text
Condition: Is above 0
Alert state if no data or all values are null: Normal
```

This avoids Insufficient Data when that anomaly is not present.

---

## 15. Email Notification Setup in Grafana

Go to:

```text
Alerting → Notification configuration → Contact points
```

Create or edit:

```text
Local Alert Contact
```

Choose email and add the developer email address.

If email delivery fails, configure SMTP in Grafana.

Open config:

```bash
sudo nano /etc/grafana/grafana.ini
```

If `[smtp]` is not found, add it at the bottom:

```ini
[smtp]
enabled = true
host = smtp.gmail.com:587
user = your_email@gmail.com
password = YOUR_GOOGLE_APP_PASSWORD
from_address = your_email@gmail.com
from_name = Grafana Alerts
startTLS_policy = OpportunisticStartTLS
```

Save and restart Grafana:

```bash
sudo systemctl restart grafana-server
```

Test the contact point again from Grafana.

Important: For Gmail, use a Google App Password, not the normal Gmail password.

---

## 16. Testing the Project

To test a fixed anomaly, open `website_metrics.py`:

```bash
nano website_metrics.py
```

Change:

```python
TEST_MODE = "random"
```

to:

```python
TEST_MODE = "backend_overload"
```

Restart the website metrics exporter:

```bash
python3 website_metrics.py
```

Wait 30 to 60 seconds.

Grafana should show:

```text
agent_overall_anomaly = 1
anomaly_type = backend_overload
severity = critical
recommendation = scale_or_restart_backend
```

Alert state should move:

```text
Normal → Pending → Firing
```

---

## 17. Meaning of Important Metrics

| Metric | Meaning |
|---|---|
| `website_up` | 1 means website is running, 0 means website is down |
| `website_response_time_ms` | Website response time in milliseconds |
| `website_error_rate_percent` | Error rate percentage |
| `website_requests_per_minute` | Website traffic |
| `agent_overall_anomaly` | 0 means normal, 1 means anomaly detected |
| `agent_anomaly_score` | Anomaly score from 0 to 100 |
| `agent_anomaly_detail` | Root cause, severity, recommendation, and action |
| `agent_ai_answer` | AI-style explanation generated by the local agent |
| `agent_anomaly_events_total` | Total count of detected anomaly events |

---

## 18. Example Agent Output

Example Prometheus result:

```text
{action="debug_errors", agent="Anomaly Detection Agent", anomaly_type="high_error_rate", instance="localhost:8001", job="agentic_anomaly_agent", location="application_layer", recommendation="check_application_logs", severity="critical"}
```

Meaning:

```text
The agent detected a high error rate anomaly.
The problem is in the application layer.
Severity is critical.
Recommended action is to check application logs and debug errors.
```

---

## 19. Troubleshooting

### Problem: Grafana alert shows No Data or Insufficient Data

Use:

```promql
or vector(0)
```

Example:

```promql
max_over_time(agent_anomaly_detail{anomaly_type="traffic_spike"}[5m]) or vector(0)
```

Also set:

```text
Alert state if no data or all values are null: Normal
```

### Problem: Agent metrics not visible

Check if agent is running:

```bash
curl http://localhost:8001/metrics
```

Check Prometheus target:

```text
http://localhost:9090/targets
```

### Problem: Website metrics not visible

Check exporter:

```bash
curl http://localhost:8000/metrics
```

Check Prometheus target:

```text
http://localhost:9090/targets
```

### Problem: Email alert failed

Check SMTP configuration:

```bash
sudo nano /etc/grafana/grafana.ini
```

Restart Grafana:

```bash
sudo systemctl restart grafana-server
```

Check logs:

```bash
sudo journalctl -u grafana-server -n 50 --no-pager
```

---

## 20. Final Project Explanation

This project implements a real-time agentic AI approach for website traffic anomaly detection. Website metrics are exposed through a Python exporter and collected by Prometheus. A local Python-based agentic system continuously reads the latest metrics from Prometheus, detects anomalies, identifies the root cause, classifies severity, recommends action, and generates an AI-style explanation.

Grafana displays the real-time website metrics, agent decisions, root cause details, anomaly count, and alerts. When an anomaly is detected, Grafana can notify developers through configured contact points such as email, Slack, Telegram, or webhook.

The system does not require any external API key because the agentic logic runs locally and uses the local Prometheus HTTP API.

---

## 21. Project Title

```text
Agentic AI-Based Website Traffic Anomaly Detection and Root Cause Analysis using Grafana and Prometheus
```
