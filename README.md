---
# Clinical Summary Generator (FastAPI + Streamlit + LLM)

A Clinical Summary Generator application that ingests simplified EHR data from CSV files and uses an LLM to generate a structured, evidence-based clinical summary **with citations**.

This project follows a clean layered architecture:
- **Data Layer**: Load & query CSV tables like a relational database
- **Core Logic**: Build clinical context + call LLM to generate summary
- **Access Points**:
  - **FastAPI Backend** (`POST /generate_summary`)
  - **Streamlit Frontend UI** (calls the backend)

---

## ✨ Key Features

- Ingests EHR data from:
  - `diagnoses.csv`, `medications.csv`, `vitals.csv`, `notes.csv`, `wounds.csv`, `oasis.csv`
- Filters/query data by `patient_id`
- Generates a structured clinical summary focusing on:
  - Primary diagnoses
  - Recent vital sign patterns
  - Active wounds and wound status
  - Medication list and clinical context
  - Functional status (OASIS)
  - Recent clinician notes
- **Evidence-based citations** in output (ex: `[Source: vitals.csv | visit_date=2026-01-08]`)
- FastAPI documentation available via Swagger UI (`/docs`)
- Streamlit UI with Summary / Citations / Debug tabs

---

## 📁 Project Structure

```

.
├── data/
│   ├── diagnoses.csv
│   ├── medications.csv
│   ├── vitals.csv
│   ├── notes.csv
│   ├── wounds.csv
│   └── oasis.csv
│
├── src/
│   ├── **__init__**.py
│   ├── data_loader.py          # Load + dtype correction
│   ├── patient_service.py      # Query/filter by patient_id/episode_id
│   ├── summarizer.py           # Transform raw tables -> structured summary inputs
│   ├── prompt_builder.py       # Build LLM prompt/context string with citations
│   ├── llm_client.py           # OpenAI LLM call (robust param handling)
│   └── summary_generator.py    # Pipeline: load -> summarize -> LLM -> output
│
├── main.py                     # FastAPI backend (POST /generate_summary)
├── app.py                      # Streamlit frontend (calls backend)
├── requirements.txt
└── README.md

````

---

## 🧠 Pipeline Overview (How it Works)

### 1) Data Loading
`src/data_loader.py`
- Loads all CSVs into pandas DataFrames
- Fixes incorrect datatypes:
  - Date columns → `datetime64`
  - Numeric columns → `float`
  - IDs → nullable integers
- Returns a dictionary of tables:
  ```python
  {
    "diagnoses": df,
    "medications": df,
    "vitals": df,
    "notes": df,
    "wounds": df,
    "oasis": df
  }
````

---

### 2) Patient Query Layer

`src/patient_service.py`

* Filters tables like a relational database
* Supports:

  * `patient_exists()`
  * `get_patient_bundle(patient_id)`
  * `get_latest_episode_id(patient_id)`
  * `get_episode_bundle(patient_id, episode_id)`

---

### 3) Summarization Preprocessing

`src/summarizer.py`

* Converts raw patient data into structured summary inputs:

  * latest vitals per vital type + abnormal flags
  * wound list + onset/visit dates
  * latest OASIS assessment
  * top recent clinical notes
  * deduplicated medication list

---

### 4) Prompt Building (Context String)

`src/prompt_builder.py`

* Builds an LLM-ready context string
* Enforces citation rules:

  * every claim must include source file and date when available
* Produces structured instruction headings:

  * Patient Overview, Diagnoses, Vitals, Wounds, Medications, OASIS, Notes, Risks, Care Focus

---

### 5) LLM Summary Generation

`src/llm_client.py` + `src/summary_generator.py`

* Sends the prompt/context string to the LLM (OpenAI)
* Handles model differences safely (e.g., retry if `temperature` unsupported)
* Fallback template generator exists to keep the system runnable even if LLM fails

---

## ✅ Setup Instructions

### 1) Create Virtual Environment

**Windows (PowerShell)**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

---

### 2) Install Dependencies

```powershell
pip install -r requirements.txt
```

---

### 3) Set OpenAI API Key

**PowerShell (temporary for current terminal session)**

```powershell
$env:OPENAI_API_KEY="YOUR_KEY_HERE"
```

**PowerShell (permanent)**

```powershell
setx OPENAI_API_KEY "YOUR_KEY_HERE"
```

> After using `setx`, restart VS Code/terminal.

Verify:

```powershell
echo $env:OPENAI_API_KEY
```

---

## 🚀 Run the Application

### Terminal 1 — Start FastAPI Backend

From project root:

```powershell
uvicorn main:app --reload
```

Backend should run at:

* `http://127.0.0.1:8000`

Swagger documentation:

* `http://127.0.0.1:8000/docs`

Health check:

* `http://127.0.0.1:8000/health`

---

### Terminal 2 — Start Streamlit Frontend

From project root:

```powershell
streamlit run app.py
```

Frontend runs at:

* `http://localhost:8501`

---

## 🔌 API Usage

### Endpoint

**POST** `/generate_summary`

### Example Body

```json
{
  "patient_id": 1002,
  "use_llm": true,
  "model": "gpt-4o-mini"
}
```

### Example Response

```json
{
  "patient_id": 1002,
  "summary": ".... clinical summary text ...",
  "debug": {
    "episode_id": 5002,
    "llm_status": "success"
  }
}
```

---

## 🧪 Common Troubleshooting

### 1) "OPENAI_API_KEY not found"

Make sure the environment variable is set:

```powershell
echo $env:OPENAI_API_KEY
```

If not visible in VS Code terminal:

* close VS Code completely
* reopen and activate venv again

---

### 2) PowerShell curl errors

PowerShell uses `Invoke-WebRequest` as `curl`.
Use:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/generate_summary" -Method Post -ContentType "application/json" -Body '{"patient_id":1002,"use_llm":true,"model":"gpt-4o-mini"}'
```

---

## 📌 Notes on Citations (Bonus Requirement)

The prompt instructs the LLM:

* Every sentence/bullet must include citations
* Citations follow:

  * `[Source: <file>.csv | <date_field>=<date>]`

Example:

* Blood pressure elevated (145/88 on 2026-01-08) `[Source: vitals.csv | visit_date=2026-01-08]`

---
