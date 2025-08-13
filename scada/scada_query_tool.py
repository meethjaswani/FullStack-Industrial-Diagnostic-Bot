import os
import requests
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
from typing import Optional, Dict, Any
import numpy as np

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Adjust path for LangGraph compatibility
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(base_dir, "data", "scada_data.db")

month_map = {
    "january": "01", "february": "02", "march": "03", "april": "04",
    "may": "05", "june": "06", "july": "07", "august": "08",
    "september": "09", "october": "10", "november": "11", "december": "12"
}

def extract_month(q: str) -> Optional[str]:
    for month_name, month_num in month_map.items():
        if month_name in q:
            return month_num
    return None

def process_custom_scada_data(df: pd.DataFrame, question: str, month_filter: Optional[str] = None) -> str:
    """Process custom SCADA data and answer questions about it"""
    try:
        # Basic data validation
        if df.empty:
            return "The uploaded SCADA data is empty. Please check your file."
        
        # Show basic data info
        total_records = len(df)
        date_columns = [col for col in df.columns if 'date' in col.lower() or 'time' in col.lower()]
        
        # Filter by month if specified
        if month_filter and date_columns:
            # Try to find a date column and filter by month
            for date_col in date_columns:
                try:
                    df[date_col] = pd.to_datetime(df[date_col])
                    df_filtered = df[df[date_col].dt.month == month_filter]
                    if not df_filtered.empty:
                        df = df_filtered
                        break
                except:
                    continue
        
        # Answer based on question type
        q = question.lower()
        
        if 'count' in q or 'how many' in q:
            return f"Total records in the uploaded SCADA data: {total_records}"
        
        elif 'columns' in q or 'fields' in q:
            columns = list(df.columns)
            return f"Available columns in the uploaded data: {', '.join(columns)}"
        
        elif 'sample' in q or 'first' in q or 'preview' in q:
            sample_data = df.head(5).to_dict('records')
            return f"Sample data (first 5 records): {sample_data}"
        
        elif 'summary' in q or 'overview' in q:
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            summary_stats = df[numeric_cols].describe() if len(numeric_cols) > 0 else "No numeric columns found"
            return f"Data summary: {total_records} records, {len(df.columns)} columns. Numeric summary: {summary_stats}"
        
        else:
            # Try to find relevant information based on question keywords
            relevant_cols = []
            for col in df.columns:
                if any(keyword in col.lower() for keyword in q.split()):
                    relevant_cols.append(col)
            
            if relevant_cols:
                sample_values = df[relevant_cols].head(3).to_dict('records')
                return f"Found relevant columns: {', '.join(relevant_cols)}. Sample values: {sample_values}"
            else:
                return f"Uploaded SCADA data contains {total_records} records with {len(df.columns)} columns. Please ask specific questions about the data."
                
    except Exception as e:
        return f"Error processing custom SCADA data: {str(e)}"

def query_scada(nl_question: str, custom_data: Optional[Dict[str, Any]] = None) -> str:
    q = nl_question.lower()
    month_filter = extract_month(q)
    query = None
    
    # Use custom data if provided, otherwise use default database
    if custom_data and custom_data.get('data'):
        # Process custom data
        df = pd.DataFrame(custom_data['data'])
        return process_custom_scada_data(df, nl_question, month_filter)
    
    # Use default database
    engine = create_engine(f"sqlite:///{DB_PATH}")

    if any(word in q for word in ["pressure", "psi", "capper", "compressor", "bar", "leak"]):
        query = "SELECT * FROM scada_logs WHERE metric_name='pressure_psi'"
    elif any(word in q for word in ["temperature", "temp", "celsius", "overheat", "boiler", "furnace", "chiller"]):
        query = "SELECT * FROM scada_logs WHERE metric_name='temperature_celsius'"
    elif any(word in q for word in ["vibration", "shake", "hz", "unbalance", "resonance", "oscillation"]):
        query = "SELECT * FROM scada_logs WHERE metric_name='vibration_hz'"
    elif any(word in q for word in ["load", "power", "grid", "electric", "kw", "average load", "main supply"]):
        query = "SELECT AVG(value) as avg_kw FROM scada_logs WHERE metric_name='load_kw'"
    elif any(word in q for word in ["rpm", "rotation", "overspeed", "underspeed", "shaft speed"]):
        query = "SELECT * FROM scada_logs WHERE metric_name='rpm'"
    elif any(word in q for word in ["error", "anomaly", "fault", "issue", "warning", "alarm", "problem", "503", "504", "505"]):
        query = "SELECT * FROM scada_logs WHERE error_code IS NOT NULL"

    if query:
        if month_filter:
            query += f" AND strftime('%m', timestamp) = '{month_filter}'"
        if "AVG" not in query:
            query += " ORDER BY timestamp DESC LIMIT 10;"
        else:
            query += ";"
    else:
        return fallback_response(nl_question)

    try:
        df = pd.read_sql(query, engine)
    except Exception as e:
        return f"❌ SQL Query Error: {str(e)}"

    if df.empty:
        return "⚠️ No data matched your query."

    result_text = df.to_string(index=False)
    return explain_data_with_llm(result_text)

def fallback_response(nl_question: str) -> str:
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "llama3-8b-8192",
            "messages": [
                {"role": "system", "content": "You are a SCADA diagnostics assistant."},
                {"role": "user", "content": nl_question}
            ],
            "temperature": 0.4
        }
    )
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return f"❌ Groq fallback error: {response.text}"

def explain_data_with_llm(data_str: str) -> str:
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "llama3-8b-8192",
            "messages": [
                {"role": "system", "content": "You are a helpful diagnostics assistant. Analyze the SCADA data and explain it simply."},
                {"role": "user", "content": f"Explain this data:\n\n{data_str}"}
            ],
            "temperature": 0.3
        }
    )
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return f"❌ Groq API error: {response.text}"

# ✅ For manual testing only
if __name__ == "__main__":
    while True:
        question = input("🔍 Ask a SCADA question (or 'exit'): ").strip()
        if question.lower() == "exit":
            break
        print(query_scada(question))
