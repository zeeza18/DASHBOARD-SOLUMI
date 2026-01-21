# app.py (backend) - replicated AI-driven logic from root app.py with SPA serving from frontend/dist
from flask import Flask, request, jsonify, send_from_directory, send_file
import psycopg2
from openai import OpenAI
from dotenv import load_dotenv
import os
import re
import json
from datetime import datetime
from pathlib import Path

load_dotenv()  # load values from .env if present

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "frontend" / "dist"
TEMP_STORE_DIR = BASE_DIR / "temp_store"
CHAT_STORE_DIR = BASE_DIR / "TEMP_STORAGE"

app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="")

# Restrict file serving; set FILE_BASE_PATH in .env if files live elsewhere (e.g., C:\Users\Owner\Desktop)
ALLOWED_BASE_PATH = os.path.abspath(os.getenv("FILE_BASE_PATH", os.getcwd()))

# Configuration (env-driven, defaults match original root app.py)
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5433")),
    "database": os.getenv("DB_NAME", "bismillah"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "Chicago@1713"),
}
DB_CONNECT_TIMEOUT = int(os.getenv("DB_CONNECT_TIMEOUT", "5"))

# Initialize OpenAI client (supports OPENAI_API_KEY or OPENAI_API)
openai_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API")
if not openai_key:
    raise RuntimeError("Missing OPENAI_API_KEY (or OPENAI_API) environment variable.")
client = OpenAI(api_key=openai_key)

# Enhanced System Prompt with AND/OR logic (copied from root app.py)
SYSTEM_PROMPT = """You are a PostgreSQL expert specializing in generating SQL queries for a medical laboratory document database.

================================================================================
DATABASE SCHEMA: uml_temp
================================================================================

Table: uml_temp
Columns:
  - id (SERIAL PRIMARY KEY)
  - account (TEXT) - User email addresses, typically @usmedlab.org
  - filename (TEXT) - Original file names with extensions (.xlsx, .docx, .pdf, etc.)
  - filepath (TEXT) - Full Windows file paths (C:\\Users\\Owner\\Desktop\\...)
  - name (TEXT) - Person/patient names mentioned in documents
  - date (TEXT) - Dates mentioned in documents
  - dob (TEXT) - Date of birth information
  - email (TEXT) - Email addresses found in documents
  - company (TEXT) - Company/organization names
  - category (TEXT) - Document categories
  - description (TEXT) - Full text content extracted from documents
  - created_at (TIMESTAMP) - Record creation timestamp

================================================================================
DATA QUALITY ISSUES & INCONSISTENCIES
================================================================================

1. NAME FIELD (name column):
   - Inconsistent capitalization: "umair", "Umair", "UMAIR"
   - Spelling errors: "Umar", "umeir", "umaeR"
   - Multiple names in one field
   - Often EMPTY even when names exist in description
   - Solution: Always search BOTH name column AND description with case-insensitive fuzzy matching

2. DATE FIELD (date column):
   - Multiple formats coexist:
     * "june 2023", "jun 2023", "June 2023"
     * "1/1/2025", "01/01/2025", "1-1-2025", "01-01-2025"
     * "january 1, 2025", "jan 1 2025", "January 1st, 2025"
     * "2025-01-01" (ISO format)
   - Often EMPTY even when dates exist in description
   - Solution: Use regex patterns for flexible matching in BOTH date column AND description

3. DOB FIELD (dob column):
   - Same format inconsistencies as date field
   - Often EMPTY
   - Solution: Same approach as date field

4. EMAIL FIELD (email column):
   - Generally reliable (contains @ symbol)
   - Minor spelling errors possible in domain names
   - Solution: Use ILIKE with wildcards for flexibility

5. COMPANY FIELD (company column):
   - MAJOR VARIATIONS for same entities (ALWAYS include ALL variations):
     * "SEM" = "seem elahi" = "seema md" = "Seema Elahi" = "Dr Seema"
     * "MMM" = "mmm" = "MMM Diagnostics Center" = "MMM Diagnostic" = "mmm diagnostics"
     * "UML" = "uml" = "US Medical Labs" = "US Medical Laboratory" = "USMedLab" = "U.S. Medical Labs" = "US MedLab" = "US Med Labs" = "USMed" = "UMedLab" = "U Medical Labs" = "US-Medical" = "usmedlab" = "us medical labs" = "us medical lab"
     * "BCBS" = "Blue Cross Blue Shield" = "BlueCross" = "Blue Cross"
     * "Aetna" = "aetna better health" = "Aetna Better" = "AETNA"
     * "UHC" = "United Health Care" = "UnitedHealthcare" = "United Healthcare"
   - Spelling errors common: "medcial", "medlab", "meical"
   - Solution: Use multiple OR conditions with ILIKE and partial matching for ALL variations

6. CATEGORY FIELD (category column):
   - Known valid categories (with common misspellings):
     * "Human Resources" / "Human Resource" / "HR" / "human resources"
     * "Billing and Revenue Management" / "Billing & Revenue" / "billing"
     * "Financial Management" / "Financial Mgmt" / "finance"
     * "Operations & Administration" / "Operations and Administration" / "Ops & Admin"
     * "Legal & Compliance" / "Legal and Compliance" / "Compliance"
     * "Supply & Vendor Management" / "Supply and Vendor" / "Vendor Management"
     * "Patient Care & Records" / "Patient Care" / "patient records"
     * "Transportation Services" / "Transport" / "Logistics"
   - OCR/font errors cause spelling variations
   - Solution: Use similarity matching or multiple ILIKE patterns

7. DESCRIPTION FIELD (description column):
   - MOST RELIABLE field - contains full document text
   - Can be very long (up to 32,000+ characters)
   - Contains dates, names, emails, companies even if other fields are empty
   - Solution: ALWAYS include description in searches as primary source

================================================================================
SQL QUERY GENERATION RULES - CRITICAL AND/OR LOGIC
================================================================================

1. ALWAYS USE CASE-INSENSITIVE MATCHING:
   - Use LOWER() function for exact matching
   - Use ILIKE instead of LIKE (case-insensitive pattern matching)
   - Use ~* for case-insensitive regex matching

2. FOR NAME SEARCHES:
   - Search BOTH name column AND description
   - Use ILIKE with wildcards: '%searchterm%'
   - Example: WHERE LOWER(name) LIKE LOWER('%umair%') OR LOWER(description) LIKE LOWER('%umair%')

3. FOR DATE RANGE SEARCHES - CRITICAL AND LOGIC:
   **IMPORTANT**: When user specifies a date range (e.g., "june 2023 to july 2025"), 
   the month AND year must BOTH be present in the same field.
   
   **WRONG** (matches "june 2022" because it finds "june" and "2023" separately):
   WHERE date ~* 'june|jun' AND date ~* '2023|2024|2025'
   
   **CORRECT** (ensures month and year are together):
   WHERE (date ~* '(june|jun)[^0-9]*(2023|2024|2025)' 
      OR date ~* '(july|jul)[^0-9]*(2023|2024|2025)')
   OR (description ~* '(june|jun)[^0-9]*(2023|2024|2025)' 
      OR description ~* '(july|jul)[^0-9]*(2023|2024|2025)')
   
   For numeric date ranges (e.g., "01/2023 to 07/2025"):
   WHERE (date ~* '(06|6|07|7)[/-](2023|2024|2025)')
      OR (description ~* '(06|6|07|7)[/-](2023|2024|2025)')
   
   Key patterns:
   - [^0-9]* allows spaces, commas, or other separators between month and year
   - Parentheses group month variations (june|jun) with their years
   - Use OR between different month conditions
   - Always check BOTH date column AND description

4. FOR COMPANY SEARCHES:
   - Include ALL known variations in OR conditions
   - Example for "UML":
     WHERE company ILIKE '%UML%' 
        OR company ILIKE '%US Medical Labs%'
        OR company ILIKE '%USMedLab%'
        OR description ILIKE '%UML%'
        OR description ILIKE '%US Medical Labs%'

5. FOR CATEGORY SEARCHES:
   - Include common spelling variations
   - Example for "Legal & Compliance":
     WHERE category ILIKE '%legal%compliance%'
        OR category ILIKE '%legal and compliance%'
        OR category ILIKE '%compliance%'
        OR description ILIKE '%legal%compliance%'

6. FOR DOCUMENT TYPE/CONTENT SEARCHES:
   **When user mentions document types (invoice, bill, statement, report, etc.),
   these are CONTENT requirements and must be in the WHERE clause**

   Example: "bank statements for UML from 2025"
   WHERE (description ILIKE '%bank%statement%' OR description ILIKE '%bank statement%'
      OR category ILIKE '%bank%' OR filename ILIKE '%bank%statement%')
     AND (company ILIKE '%UML%' OR description ILIKE '%UML%')
     AND (date ~* '2025' OR description ~* '2025')

   Example: "invoices from january 2024"
   WHERE (description ILIKE '%invoice%' OR filename ILIKE '%invoice%' OR category ILIKE '%invoice%')
     AND (date ~* '(january|jan)[^0-9]*2024' OR description ~* '(january|jan)[^0-9]*2024')

7. FOR COMBINED CONDITIONS (Multiple filters):
   **Use proper AND/OR grouping with parentheses**

   Example: "Legal documents from UML in 2024"
   WHERE (category ILIKE '%legal%' OR description ILIKE '%legal%')
     AND (company ILIKE '%UML%' OR company ILIKE '%US Medical Labs%' OR description ILIKE '%UML%')
     AND (date ~* '2024' OR description ~* '2024')

   Example: "Documents for Umair or John from june 2023"
   WHERE ((LOWER(name) LIKE '%umair%' OR LOWER(description) LIKE '%umair%')
       OR (LOWER(name) LIKE '%john%' OR LOWER(description) LIKE '%john%'))
     AND (date ~* '(june|jun)[^0-9]*2023' OR description ~* '(june|jun)[^0-9]*2023')

8. ALWAYS ADD A MATCH_REASON COLUMN:
   **CRITICAL: Every query MUST include a match_reason column that explains why each row was selected**

   Use CONCAT_WS with CASE statements to build the explanation:

   SELECT *,
     CONCAT_WS(' | ',
       CASE WHEN category ILIKE '%search_term%' THEN 'Category matched: search_term' END,
       CASE WHEN description ILIKE '%search_term%' THEN 'Description matched: search_term' END,
       CASE WHEN company ILIKE '%company_name%' THEN 'Company matched: company_name' END,
       CASE WHEN date ~* 'date_pattern' THEN 'Date matched: date_pattern' END,
       CASE WHEN name ILIKE '%name_term%' THEN 'Name matched: name_term' END
     ) as match_reason
   FROM uml_temp
   WHERE (your conditions)

   - Use ' | ' as separator for readability
   - Include CASE for each major condition in your WHERE clause
   - Use human-readable labels like "Category matched: compliance"
   - The match_reason column helps users understand why results were returned

9. ALWAYS RETURN ALL COLUMNS:
   - Use SELECT *, match_reason_column FROM uml_temp WHERE ...
   - Never use LIMIT unless explicitly requested

10. FOR EMPTY/NULL CHECKS:
   - Remember many fields can be empty string ('') or NULL
   - Example: WHERE (name IS NULL OR name = '' OR LOWER(name) LIKE '%search%')

================================================================================
EXAMPLE QUERIES WITH PROPER AND/OR LOGIC
================================================================================

Example 1: "Find all files from june 2023 to july 2025"
SELECT *,
  CONCAT_WS(' | ',
    CASE WHEN date ~* '(june|jun)[^0-9]*(2023|2024|2025)' THEN 'Date field: june 2023-2025' END,
    CASE WHEN date ~* '(july|jul)[^0-9]*(2023|2024|2025)' THEN 'Date field: july 2023-2025' END,
    CASE WHEN description ~* '(june|jun)[^0-9]*(2023|2024|2025)' THEN 'Description: june 2023-2025' END,
    CASE WHEN description ~* '(july|jul)[^0-9]*(2023|2024|2025)' THEN 'Description: july 2023-2025' END
  ) as match_reason
FROM uml_temp
WHERE (date ~* '(june|jun)[^0-9]*(2023|2024|2025)'
   OR date ~* '(july|jul)[^0-9]*(2023|2024|2025)')
   OR (description ~* '(june|jun)[^0-9]*(2023|2024|2025)'
   OR description ~* '(july|jul)[^0-9]*(2023|2024|2025)');

Example 2: "List files with name Star boy"
SELECT *,
  CONCAT_WS(' | ',
    CASE WHEN LOWER(name) LIKE LOWER('%star%boy%') THEN 'Name field: star boy' END,
    CASE WHEN LOWER(description) LIKE LOWER('%star%boy%') THEN 'Description: star boy' END,
    CASE WHEN LOWER(name) LIKE LOWER('%starboy%') THEN 'Name field: starboy' END,
    CASE WHEN LOWER(description) LIKE LOWER('%starboy%') THEN 'Description: starboy' END
  ) as match_reason
FROM uml_temp
WHERE LOWER(name) LIKE LOWER('%star%boy%')
   OR LOWER(description) LIKE LOWER('%star%boy%')
   OR LOWER(name) LIKE LOWER('%starboy%')
   OR LOWER(description) LIKE LOWER('%starboy%');

Example 3: "Give me all Legal and Compliance documents"
SELECT *,
  CONCAT_WS(' | ',
    CASE WHEN category ILIKE '%legal%compliance%' THEN 'Category: legal & compliance' END,
    CASE WHEN category ILIKE '%legal%' THEN 'Category: legal' END,
    CASE WHEN category ILIKE '%compliance%' THEN 'Category: compliance' END,
    CASE WHEN description ILIKE '%legal%compliance%' THEN 'Description: legal & compliance' END
  ) as match_reason
FROM uml_temp
WHERE category ILIKE '%legal%compliance%'
   OR category ILIKE '%legal%'
   OR category ILIKE '%compliance%'
   OR description ILIKE '%legal%compliance%';

Example 4: "Find UML documents from 2024"
SELECT *,
  CONCAT_WS(' | ',
    CASE WHEN company ILIKE '%UML%' THEN 'Company: UML' END,
    CASE WHEN company ILIKE '%US Medical Labs%' THEN 'Company: US Medical Labs' END,
    CASE WHEN description ILIKE '%US Medical Labs%' THEN 'Description: US Medical Labs' END,
    CASE WHEN description ILIKE '%UML%' THEN 'Description: UML' END,
    CASE WHEN date ~* '2024' THEN 'Date field: 2024' END,
    CASE WHEN description ~* '2024' THEN 'Description: 2024' END
  ) as match_reason
FROM uml_temp
WHERE (company ILIKE '%UML%'
   OR company ILIKE '%US Medical Labs%'
   OR description ILIKE '%US Medical Labs%'
   OR description ILIKE '%UML%')
   AND (date ~* '2024' OR description ~* '2024');

Example 5: "Show billing documents for Umair from march 2024"
SELECT *,
  CONCAT_WS(' | ',
    CASE WHEN category ILIKE '%billing%' THEN 'Category: billing' END,
    CASE WHEN description ILIKE '%billing%' THEN 'Description: billing' END,
    CASE WHEN LOWER(name) LIKE '%umair%' THEN 'Name field: umair' END,
    CASE WHEN LOWER(description) LIKE '%umair%' THEN 'Description: umair' END,
    CASE WHEN date ~* '(march|mar)[^0-9]*2024' THEN 'Date field: march 2024' END,
    CASE WHEN description ~* '(march|mar)[^0-9]*2024' THEN 'Description: march 2024' END
  ) as match_reason
FROM uml_temp
WHERE (category ILIKE '%billing%' OR description ILIKE '%billing%')
   AND (LOWER(name) LIKE '%umair%' OR LOWER(description) LIKE '%umair%')
   AND (date ~* '(march|mar)[^0-9]*2024' OR description ~* '(march|mar)[^0-9]*2024');

Example 6: "Documents from january to december 2023"
SELECT *,
  CONCAT_WS(' | ',
    CASE WHEN date ~* '(january|jan|february|feb|march|mar|april|apr|may|june|jun|july|jul|august|aug|september|sep|october|oct|november|nov|december|dec)[^0-9]*2023' THEN 'Date field: 2023' END,
    CASE WHEN description ~* '(january|jan|february|feb|march|mar|april|apr|may|june|jun|july|jul|august|aug|september|sep|october|oct|november|nov|december|dec)[^0-9]*2023' THEN 'Description: 2023' END
  ) as match_reason
FROM uml_temp
WHERE (date ~* '(january|jan|february|feb|march|mar|april|apr|may|june|jun|july|jul|august|aug|september|sep|october|oct|november|nov|december|dec)[^0-9]*2023')
   OR (description ~* '(january|jan|february|feb|march|mar|april|apr|may|june|jun|july|jul|august|aug|september|sep|october|oct|november|nov|december|dec)[^0-9]*2023');

Example 7: "Bank statements for UML from january 2025 to july 2025"
SELECT *,
  CONCAT_WS(' | ',
    CASE WHEN description ILIKE '%bank%statement%' THEN 'Description: bank statement' END,
    CASE WHEN category ILIKE '%bank%' THEN 'Category: bank' END,
    CASE WHEN filename ILIKE '%bank%statement%' THEN 'Filename: bank statement' END,
    CASE WHEN company ILIKE '%UML%' THEN 'Company: UML' END,
    CASE WHEN company ILIKE '%US Medical Labs%' THEN 'Company: US Medical Labs' END,
    CASE WHEN description ILIKE '%UML%' THEN 'Description: UML' END,
    CASE WHEN date ~* '(january|jan|february|feb|march|mar|april|apr|may|june|jun|july|jul)[^0-9]*(2025)' THEN 'Date field: jan-jul 2025' END,
    CASE WHEN description ~* '(january|jan|february|feb|march|mar|april|apr|may|june|jun|july|jul)[^0-9]*(2025)' THEN 'Description: jan-jul 2025' END
  ) as match_reason
FROM uml_temp
WHERE (description ILIKE '%bank%statement%' OR description ILIKE '%bank statement%'
   OR category ILIKE '%bank%' OR filename ILIKE '%bank%statement%')
   AND (company ILIKE '%UML%' OR company ILIKE '%US Medical Labs%'
   OR description ILIKE '%US Medical Labs%' OR description ILIKE '%UML%')
   AND ((date ~* '(january|jan)[^0-9]*(2025)'
   OR date ~* '(february|feb)[^0-9]*(2025)'
   OR date ~* '(march|mar)[^0-9]*(2025)'
   OR date ~* '(april|apr)[^0-9]*(2025)'
   OR date ~* '(may)[^0-9]*(2025)'
   OR date ~* '(june|jun)[^0-9]*(2025)'
   OR date ~* '(july|jul)[^0-9]*(2025)')
   OR (description ~* '(january|jan)[^0-9]*(2025)'
   OR description ~* '(february|feb)[^0-9]*(2025)'
   OR description ~* '(march|mar)[^0-9]*(2025)'
   OR description ~* '(april|apr)[^0-9]*(2025)'
   OR description ~* '(may)[^0-9]*(2025)'
   OR description ~* '(june|jun)[^0-9]*(2025)'
   OR description ~* '(july|jul)[^0-9]*(2025)'));

Example 8: "Give me all documents related to compliance and how US Medical labs prevented fraud"
SELECT *,
  CONCAT_WS(' | ',
    CASE WHEN category ILIKE '%compliance%' THEN 'Category: compliance' END,
    CASE WHEN description ILIKE '%compliance%' THEN 'Description: compliance' END,
    CASE WHEN description ILIKE '%fraud%' THEN 'Description: fraud' END,
    CASE WHEN description ILIKE '%prevent%' THEN 'Description: prevent/prevention' END,
    CASE WHEN company ILIKE '%UML%' THEN 'Company: UML' END,
    CASE WHEN company ILIKE '%US Medical Labs%' THEN 'Company: US Medical Labs' END,
    CASE WHEN description ILIKE '%US Medical Labs%' THEN 'Description: US Medical Labs' END,
    CASE WHEN description ILIKE '%UML%' THEN 'Description: UML' END
  ) as match_reason
FROM uml_temp
WHERE (category ILIKE '%compliance%' OR description ILIKE '%compliance%')
   AND (description ILIKE '%fraud%' OR description ILIKE '%prevent%')
   AND (company ILIKE '%UML%' OR company ILIKE '%uml%'
   OR company ILIKE '%US Medical Labs%' OR company ILIKE '%USMedLab%'
   OR company ILIKE '%US MedLab%' OR company ILIKE '%usmedlab%'
   OR description ILIKE '%US Medical Labs%' OR description ILIKE '%UML%'
   OR description ILIKE '%USMedLab%' OR description ILIKE '%usmedlab%');

================================================================================
OUTPUT FORMAT
================================================================================

Return ONLY the SQL query. No explanations, no markdown formatting, no code blocks.
Just the raw SQL query that can be executed directly.

If the user request is unclear, make reasonable assumptions based on context.
Always prefer broader searches over narrow ones due to data inconsistencies.
Use proper parentheses for AND/OR grouping to ensure correct logic.
"""

# System prompt for SUMMARY mode - document Q&A
SUMMARY_SYSTEM_PROMPT = """You are a helpful document analysis assistant for US Medical Labs.

You will be given content from one or more documents and user questions about them.

Guidelines:
- Be concise but thorough in your answers
- Cite specific information from the documents when available
- If information is not in the documents, say so clearly
- For summaries, highlight key points: dates, names, amounts, and important details
- When multiple documents are provided, clearly reference which document contains what information
- Remember previous questions in this conversation for context

Format your responses clearly with bullet points or sections when appropriate.
"""

SUMMARY_CONVERSATION_DIR = CHAT_STORE_DIR  # Reuse same storage directory


def save_summary_conversation(conversation_id: str, data: dict):
    """Save summary conversation to JSON file."""
    SUMMARY_CONVERSATION_DIR.mkdir(exist_ok=True)
    file_path = SUMMARY_CONVERSATION_DIR / f"summary_{conversation_id}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return file_path


def load_summary_conversation(conversation_id: str) -> dict:
    """Load summary conversation from JSON file."""
    file_path = SUMMARY_CONVERSATION_DIR / f"summary_{conversation_id}.json"
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


# System prompt for ANALYSE mode - data visualization and analysis
ANALYSE_SYSTEM_PROMPT = """You are a data analyst for US Medical Labs. Your job is to analyze document content and generate structured data for visualizations.

Given document content, extract meaningful data and create analysis with charts.

IMPORTANT: You must respond with VALID JSON only. No markdown, no extra text.

Response format:
{
  "analysis_text": "Your detailed analysis explanation here (use markdown formatting)",
  "charts": [
    {
      "type": "bar|line|pie|doughnut|timeline",
      "title": "Chart Title",
      "labels": ["Label1", "Label2"],
      "datasets": [
        {
          "label": "Dataset Name",
          "data": [10, 20],
          "backgroundColor": ["#6366f1", "#8b5cf6"]
        }
      ]
    }
  ],
  "tables": [
    {
      "title": "Table Title",
      "headers": ["Column1", "Column2"],
      "rows": [["Value1", "Value2"]]
    }
  ],
  "key_findings": ["Finding 1", "Finding 2"]
}

Analysis Guidelines:
1. For PATIENT VISITS: Extract dates, diagnoses, treatments. Show timeline if multiple visits.
2. For BILLING: Extract amounts, dates, reasons, payers. Show payment trends.
3. For MULTIPLE FILES: Compare across documents, show progression/changes.
4. Always include key_findings with actionable insights.
5. Use appropriate chart types:
   - Timeline/Line: For data over time
   - Bar: For comparisons
   - Pie/Doughnut: For proportions
   - Tables: For detailed breakdowns

Color palette to use:
- Primary: #6366f1 (purple)
- Secondary: #8b5cf6 (violet)
- Accent: #06b6d4 (cyan)
- Success: #10b981 (green)
- Warning: #f59e0b (orange)
- Danger: #ef4444 (red)
"""


def save_analyse_conversation(conversation_id: str, data: dict):
    """Save analyse conversation to JSON file."""
    CHAT_STORE_DIR.mkdir(exist_ok=True)
    file_path = CHAT_STORE_DIR / f"analyse_{conversation_id}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return file_path


def load_analyse_conversation(conversation_id: str) -> dict:
    """Load analyse conversation from JSON file."""
    file_path = CHAT_STORE_DIR / f"analyse_{conversation_id}.json"
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def generate_sql_query(user_query: str) -> str:
    """
    Generate SQL query from natural language using OpenAI
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_query},
            ],
            temperature=0.1,
            max_tokens=800,
        )

        sql_query = response.choices[0].message.content.strip()
        sql_query = sql_query.replace("```sql", "").replace("```", "").strip()

        return sql_query

    except Exception as e:
        return f"Error: {str(e)}"


def execute_query(sql_query: str):
    """
    Execute SQL query and return results
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG, connect_timeout=DB_CONNECT_TIMEOUT)
        cursor = conn.cursor()

        cursor.execute(sql_query)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]

        cursor.close()
        conn.close()

        return {
            "success": True,
            "columns": columns,
            "rows": rows,
            "count": len(rows),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


@app.route("/")
def index():
    # Serve the SPA entrypoint from the built frontend
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        return (
            "Frontend build missing. Run `npm install` and `npm run build` inside frontend/ before starting the backend.",
            500,
        )
    return send_from_directory(str(STATIC_DIR), "index.html")


@app.route("/open-file")
def open_file():
    """
    Serve a file from disk if it resides under ALLOWED_BASE_PATH.
    Prevents the browser from blocking file:/// links.
    """
    file_path = request.args.get("path")
    if not file_path:
        return jsonify({"error": "Missing file path"}), 400

    abs_path = os.path.abspath(file_path)
    try:
        common = os.path.commonpath([abs_path, ALLOWED_BASE_PATH])
    except ValueError:
        common = ""

    if common != ALLOWED_BASE_PATH:
        return jsonify({"error": "Access denied for this path"}), 403

    if not os.path.exists(abs_path):
        return jsonify({"error": "File not found"}), 404

    try:
        return send_file(abs_path, as_attachment=False)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/query", methods=["POST"])
def query():
    data = request.json or {}
    user_query = data.get("query", "")
    show_all = bool(data.get("show_all", False))

    if not user_query:
        return jsonify({"error": "No query provided"}), 400

    # Generate SQL
    sql_query = generate_sql_query(user_query)
    executed_sql = sql_query

    if show_all:
        # Remove LIMIT/OFFSET to fetch full result set when requested
        executed_sql = re.sub(r"limit\s+\d+(\s+offset\s+\d+)?", "", sql_query, flags=re.IGNORECASE)

    if sql_query.startswith("Error:"):
        return jsonify(
            {
                "error": sql_query,
                "sql": None,
                "results": None,
            }
        )

    # Execute SQL
    result = execute_query(executed_sql)

    if not result["success"]:
        return jsonify(
            {
                "error": result["error"],
                "sql": executed_sql,
                "results": None,
            }
        )

    # Format results for display - show ALL results with FULL descriptions
    results_data = []
    rows_to_use = result["rows"]
    for row in rows_to_use:
        row_dict = {}
        for i, col in enumerate(result["columns"]):
            row_dict[col] = row[i]
        results_data.append(row_dict)

    return jsonify(
        {
            "sql": executed_sql,
            "results": results_data,
            "total_count": result["count"],
            "returned_count": len(results_data),
            "columns": result["columns"],
        }
    )


@app.route("/run-sql", methods=["POST"])
def run_sql():
    """
    Execute a raw SQL query directly (for re-running queries from chat history).
    """
    data = request.json or {}
    sql_query = data.get("sql", "")

    if not sql_query:
        return jsonify({"error": "No SQL query provided"}), 400

    # Basic validation - only allow SELECT queries
    if not sql_query.strip().upper().startswith("SELECT"):
        return jsonify({"error": "Only SELECT queries are allowed"}), 400

    # Execute SQL
    result = execute_query(sql_query)

    if not result["success"]:
        return jsonify(
            {
                "error": result["error"],
                "sql": sql_query,
                "results": [],
            }
        )

    # Format results for display
    results_data = []
    for row in result["rows"]:
        row_dict = {}
        for i, col in enumerate(result["columns"]):
            row_dict[col] = row[i]
        results_data.append(row_dict)

    return jsonify(
        {
            "sql": sql_query,
            "results": results_data,
            "total_count": result["count"],
            "returned_count": len(results_data),
            "columns": result["columns"],
        }
    )


@app.route("/summary-chat", methods=["POST"])
def summary_chat():
    """
    SUMMARY mode: Chat with documents using their description content.
    Supports multiple files and conversation memory.
    """
    data = request.json or {}
    files = data.get("files", [])  # Array of {filename, description, ...}
    user_message = data.get("message", "")
    conversation_id = data.get("conversation_id", "")

    if not files or not user_message:
        return jsonify({"error": "Missing files or message"}), 400

    # Generate conversation ID if not provided
    if not conversation_id:
        conversation_id = f"conv_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{os.urandom(4).hex()}"

    # Load existing conversation or create new
    conversation = load_summary_conversation(conversation_id)
    if not conversation:
        conversation = {
            "id": conversation_id,
            "created_at": datetime.utcnow().isoformat(),
            "files": files,
            "messages": []
        }

    # Build document context from all files
    doc_context_parts = []
    for i, f in enumerate(files, 1):
        filename = f.get("filename", f"Document {i}")
        description = f.get("description", "No content available")
        doc_context_parts.append(f"=== Document {i}: {filename} ===\n{description}")

    documents_context = "\n\n".join(doc_context_parts)

    # Build messages for OpenAI (include conversation history)
    messages = [
        {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
        {"role": "user", "content": f"Here are the documents to analyze:\n\n{documents_context}"}
    ]

    # Add conversation history
    for msg in conversation["messages"]:
        messages.append({"role": msg["role"], "content": msg["content"]})

    # Add current user message
    messages.append({"role": "user", "content": user_message})

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.3,
            max_tokens=2000,
        )

        assistant_response = response.choices[0].message.content.strip()

        # Update conversation with new messages
        conversation["messages"].append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.utcnow().isoformat()
        })
        conversation["messages"].append({
            "role": "assistant",
            "content": assistant_response,
            "timestamp": datetime.utcnow().isoformat()
        })
        conversation["updated_at"] = datetime.utcnow().isoformat()

        # Save conversation
        save_summary_conversation(conversation_id, conversation)

        return jsonify({
            "success": True,
            "conversation_id": conversation_id,
            "response": assistant_response,
            "messages": conversation["messages"]
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "conversation_id": conversation_id
        }), 500


@app.route("/analyse-chat", methods=["POST"])
def analyse_chat():
    """
    ANALYSE mode: Analyze documents and generate visualizations.
    Returns structured data for charts and tables.
    """
    data = request.json or {}
    files = data.get("files", [])
    user_message = data.get("message", "")
    conversation_id = data.get("conversation_id", "")

    if not files:
        return jsonify({"error": "No files provided for analysis"}), 400

    # Generate conversation ID if not provided
    if not conversation_id:
        conversation_id = f"analyse_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{os.urandom(4).hex()}"

    # Load existing conversation or create new
    conversation = load_analyse_conversation(conversation_id)
    if not conversation:
        conversation = {
            "id": conversation_id,
            "created_at": datetime.utcnow().isoformat(),
            "files": files,
            "messages": []
        }

    # Build document context from all files
    doc_context_parts = []
    for i, f in enumerate(files, 1):
        filename = f.get("filename", f"Document {i}")
        description = f.get("description", "No content available")
        category = f.get("category", "Unknown")
        doc_context_parts.append(f"=== Document {i}: {filename} (Category: {category}) ===\n{description}")

    documents_context = "\n\n".join(doc_context_parts)

    # Build the analysis request
    analysis_request = user_message if user_message else "Analyze these documents and provide insights with visualizations."

    # Build messages for OpenAI
    messages = [
        {"role": "system", "content": ANALYSE_SYSTEM_PROMPT},
        {"role": "user", "content": f"Documents to analyze:\n\n{documents_context}\n\nAnalysis request: {analysis_request}"}
    ]

    # Add conversation history for follow-up
    for msg in conversation["messages"]:
        messages.append({"role": msg["role"], "content": msg["content"]})

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.3,
            max_tokens=3000,
        )

        assistant_response = response.choices[0].message.content.strip()

        # Try to parse as JSON
        analysis_data = None
        try:
            # Remove markdown code blocks if present
            clean_response = assistant_response
            if clean_response.startswith("```"):
                clean_response = re.sub(r'^```\w*\n?', '', clean_response)
                clean_response = re.sub(r'\n?```$', '', clean_response)
            analysis_data = json.loads(clean_response)
        except json.JSONDecodeError:
            # If not valid JSON, wrap in a basic structure
            analysis_data = {
                "analysis_text": assistant_response,
                "charts": [],
                "tables": [],
                "key_findings": []
            }

        # Update conversation
        conversation["messages"].append({
            "role": "user",
            "content": analysis_request,
            "timestamp": datetime.utcnow().isoformat()
        })
        conversation["messages"].append({
            "role": "assistant",
            "content": json.dumps(analysis_data),
            "timestamp": datetime.utcnow().isoformat()
        })
        conversation["updated_at"] = datetime.utcnow().isoformat()

        # Save conversation
        save_analyse_conversation(conversation_id, conversation)

        return jsonify({
            "success": True,
            "conversation_id": conversation_id,
            "analysis": analysis_data,
            "messages": conversation["messages"]
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "conversation_id": conversation_id
        }), 500


@app.route("/health")
def health():
    try:
        conn = psycopg2.connect(**DB_CONFIG, connect_timeout=DB_CONNECT_TIMEOUT)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM uml_temp;")
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return jsonify(
            {
                "status": "healthy",
                "database": "connected",
                "total_records": count,
            }
        )
    except Exception as e:
        return jsonify(
            {
                "status": "unhealthy",
                "error": str(e),
            }
        ), 500


@app.route("/<path:path>")
def spa(path: str):
    """
    Serve files from frontend/dist with SPA fallback to index.html.
    Unknown paths fall back to the built index.
    """
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        return (
            "Frontend build missing. Run `npm install` and `npm run build` inside frontend/ before starting the backend.",
            500,
        )

    candidate = STATIC_DIR / path
    if path and candidate.exists() and candidate.is_file():
        return send_from_directory(STATIC_DIR, path)
    return send_from_directory(STATIC_DIR, "index.html")


@app.post("/save-chats")
def save_chats():
    """
    Persist chat conversations to TEMP_STORAGE as JSON.
    """
    payload = request.get_json(silent=True) or {}
    chats = payload.get("chats")
    if not isinstance(chats, list):
        return jsonify({"error": "Invalid payload; 'chats' must be a list."}), 400

    try:
        CHAT_STORE_DIR.mkdir(exist_ok=True)
        # Keep only the latest snapshot to avoid duplicate merges on reload
        for fpath in CHAT_STORE_DIR.glob("chats_*.json"):
            try:
                fpath.unlink()
            except Exception:
                continue

        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        file_path = CHAT_STORE_DIR / f"chats_{timestamp}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump({"saved_at": timestamp, "chats": chats}, f, ensure_ascii=False, indent=2)
        return jsonify({"saved": True, "file": file_path.name, "path": str(file_path)})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.get("/chats")
def list_chats():
    """
    Return all stored chats from TEMP_STORAGE (merged list).
    """
    CHAT_STORE_DIR.mkdir(exist_ok=True)
    latest = None
    for file_path in sorted(CHAT_STORE_DIR.glob("chats_*.json"), reverse=True):
        latest = file_path
        break

    if not latest or not latest.exists():
        return jsonify({"chats": []})

    try:
        with open(latest, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict) and isinstance(data.get("chats"), list):
                return jsonify({"chats": data["chats"]})
    except Exception:
        return jsonify({"chats": []})

    return jsonify({"chats": []})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000, use_reloader=False)
