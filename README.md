<p align="center">
  <img src="https://img.shields.io/badge/AI-Powered-6366f1?style=for-the-badge&logo=meta&logoColor=white" alt="AI Powered"/>
  <img src="https://img.shields.io/badge/Llama_3.2-70B-orange?style=for-the-badge&logo=meta&logoColor=white" alt="Llama"/>
  <img src="https://img.shields.io/badge/Flask-Backend-000000?style=for-the-badge&logo=flask&logoColor=white" alt="Flask"/>
  <img src="https://img.shields.io/badge/PostgreSQL-Database-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL"/>
</p>

<h1 align="center">AI Document Search & Analysis Dashboard</h1>

<p align="center">
  <strong>Natural language to SQL - Search & analyze 168,000+ documents instantly</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-1.0.0-blue?style=flat-square" alt="Version"/>
  <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="License"/>
  <img src="https://img.shields.io/badge/python-3.10+-yellow?style=flat-square&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/node-18+-green?style=flat-square&logo=node.js&logoColor=white" alt="Node"/>
</p>

---

## Dashboard Preview

<p align="center">
  <img src="assets/dashboard-main.png" alt="Dashboard" width="100%"/>
</p>

<p align="center">
  <em>Three-panel layout: Conversations | Query Area | Search Results</em>
</p>

---

## AI-Generated SQL with Search Results

<p align="center">
  <img src="assets/search-results.png" alt="Search Results" width="100%"/>
</p>

<p align="center">
  <em>1,278 documents found - Fine-tuned SQL handles company aliases, date formats, and typos</em>
</p>

---

## Light Mode

<p align="center">
  <img src="assets/light-mode.png" alt="Light Mode" width="100%"/>
</p>

---

## Mobile Responsive

<p align="center">
  <img src="assets/mobile-main.png" alt="Mobile Main" width="30%"/>
  <img src="assets/mobile-search.png" alt="Mobile Search" width="30%"/>
  <img src="assets/mobile-results.png" alt="Mobile Results" width="30%"/>
</p>

---

## System Architecture

<p align="center">
  <img src="assets/architecture.svg" alt="Architecture" width="100%"/>
</p>

---

## Task Types

| Task | Description | Use Case |
|------|-------------|----------|
| **SEARCH** | Natural language document search | Find documents by date, name, company, category |
| **ANALYSE** | AI-powered data analysis with charts | Generate visualizations and insights from documents |
| **SUMMARY** | Document summarization | Get key findings and summaries |

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Conversation History** | Save and continue previous search sessions |
| **Entity Selector** | Filter by company (UML, SEM, MMM, etc.) |
| **Type Filtering** | Filter by document type |
| **Fine-tuned SQL** | Handles typos, date formats, company aliases |
| **Match Reason** | See why each document matched |
| **Export to CSV** | Download results for analysis |
| **File Preview** | Open documents directly |
| **Real-time Status** | Live database connection indicator |
| **168,992 Records** | Searchable document database |
| **Dark/Light Mode** | Theme toggle with glassmorphism UI |

---

## Search Examples

| Query Type | Example |
|------------|---------|
| **Date Range** | `"documents from june 2023 to december 2024"` |
| **By Name** | `"find all files for John Smith"` |
| **By Category** | `"legal compliance documents"` |
| **Company + Date** | `"billing documents for UML from 2024"` |
| **Bank Statements** | `"bank statements january to july 2025"` |
| **Multi-criteria** | `"HR onboarding documents 2024"` |

---

## Fine-tuned SQL Generation

Handles real-world data inconsistencies:

```
Name variations:    "umair" = "Umair" = "UMAIR" = "Umar"
Date formats:       "june 2023" = "6/2023" = "2023-06-01"
Company aliases:    "UML" = "US Medical Labs" = "USMedLab"
Categories:         "Legal & Compliance" = "legal" = "compliance"
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | Vite + Vanilla JS, Bootstrap 5, Chart.js |
| **Backend** | Flask, Python 3.10+, REST API |
| **AI** | Ollama + Llama 3.2 70B |
| **Database** | PostgreSQL |

---

## Quick Start

```bash
git clone https://github.com/zeeza18/DASHBOARD-SOLUMI.git
cd DASHBOARD-SOLUMI

# Backend
cd backend && python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Frontend
cd ../frontend && npm install && npm run build

# Run
cd .. && python backend/app.py
```

Visit `http://localhost:5000`

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Database status |
| `/query` | POST | Execute search |
| `/analyse-chat` | POST | Run analysis |
| `/summary-chat` | POST | Generate summary |
| `/save-chats` | POST | Save conversations |
| `/chats` | GET | Load conversations |
| `/open-file` | GET | Preview document |

---

## Performance

<table align="center">
  <tr>
    <td align="center"><strong>Documents</strong><br/><code>168,992</code></td>
    <td align="center"><strong>Query Time</strong><br/><code>~150ms</code></td>
    <td align="center"><strong>SQL Gen</strong><br/><code>~100ms</code></td>
    <td align="center"><strong>Accuracy</strong><br/><code>94.7%</code></td>
  </tr>
</table>

---

## License

MIT License

---

<p align="center">
  <strong>Powered by Ollama & Llama 3.2 70B</strong>
</p>
