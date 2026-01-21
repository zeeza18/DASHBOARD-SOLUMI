# app.py
from flask import Flask, request, jsonify, send_from_directory, send_file
import psycopg2
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv
import os
import re
from datetime import datetime

load_dotenv()  # load values from .env if present

app = Flask(__name__, static_folder='static')

# Restrict file serving; set FILE_BASE_PATH in .env if files live elsewhere (e.g., C:\\Users\\Owner\\Desktop)
ALLOWED_BASE_PATH = os.path.abspath(os.getenv('FILE_BASE_PATH', os.getcwd()))

# Configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': 5433,
    'database': 'bismillah',
    'user': 'postgres',
    'password': 'Chicago@1713'
}

# Initialize OpenAI client (supports OPENAI_API_KEY or OPENAI_API)
openai_key = os.getenv('OPENAI_API_KEY') or os.getenv('OPENAI_API')
if not openai_key:
    raise RuntimeError("Missing OPENAI_API_KEY (or OPENAI_API) environment variable.")
client = OpenAI(api_key=openai_key)

# Enhanced System Prompt with AND/OR logic
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

def generate_sql_query(user_query: str) -> str:
    """
    Generate SQL query from natural language using OpenAI
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_query}
            ],
            temperature=0.1,
            max_tokens=800
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
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute(sql_query)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        cursor.close()
        conn.close()
        
        return {
            'success': True,
            'columns': columns,
            'rows': rows,
            'count': len(rows)
        }
    
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

@app.route('/')
def index():
    # Serve the SPA entrypoint from the static directory
    return send_from_directory('static', 'index.html')


@app.route('/open-file')
def open_file():
    """
    Serve a file from disk if it resides under ALLOWED_BASE_PATH.
    Prevents the browser from blocking file:/// links.
    """
    file_path = request.args.get('path')
    if not file_path:
        return jsonify({'error': 'Missing file path'}), 400

    abs_path = os.path.abspath(file_path)
    try:
        common = os.path.commonpath([abs_path, ALLOWED_BASE_PATH])
    except ValueError:
        common = ''

    if common != ALLOWED_BASE_PATH:
        return jsonify({'error': 'Access denied for this path'}), 403

    if not os.path.exists(abs_path):
        return jsonify({'error': 'File not found'}), 404

    try:
        return send_file(abs_path, as_attachment=False)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/query', methods=['POST'])
def query():
    data = request.json
    user_query = data.get('query', '')
    show_all = bool(data.get('show_all', False))
    
    if not user_query:
        return jsonify({'error': 'No query provided'}), 400
    
    # Generate SQL
    sql_query = generate_sql_query(user_query)
    executed_sql = sql_query

    if show_all:
        # Remove LIMIT/OFFSET to fetch full result set when requested
        executed_sql = re.sub(r'limit\s+\d+(\s+offset\s+\d+)?', '', sql_query, flags=re.IGNORECASE)
    
    if sql_query.startswith('Error:'):
        return jsonify({
            'error': sql_query,
            'sql': None,
            'results': None
        })
    
    # Execute SQL
    result = execute_query(executed_sql)
    
    if not result['success']:
        return jsonify({
            'error': result['error'],
            'sql': executed_sql,
            'results': None
        })
    
    # Format results for display
    results_data = []
    rows_to_use = result['rows'] if show_all else result['rows'][:100]
    for row in rows_to_use:
        row_dict = {}
        for i, col in enumerate(result['columns']):
            value = row[i]
            # Truncate long descriptions
            if col == 'description' and value and len(str(value)) > 200:
                value = str(value)[:200] + '...'
            row_dict[col] = value
        results_data.append(row_dict)

    return jsonify({
        'sql': executed_sql,
        'results': results_data,
        'total_count': result['count'],
        'returned_count': len(results_data),
        'columns': result['columns']
    })

@app.route('/health')
def health():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM uml_temp;")
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'total_records': count
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
