import sqlite3
import requests
from datetime import datetime
from typing import List, Dict, Tuple
import re
from dataclasses import dataclass
import json
import random

URL = "http://localhost:8000/chat"

@dataclass
class Message:
    date: datetime
    text: str
    similarity_score: float = 0.0

def get_db_schema(db_path: str = "chat.db") -> str:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table';")
    schemas = cursor.fetchall()
    conn.close()
    
    return "\n".join(schema[0] for schema in schemas if schema[0])

def query_to_sql(query: str, schema: str, llm_endpoint: str = URL) -> str:

    prompt = f"""Given this iMessage database schema:
{schema}

Convert this question to a SQL query that finds up to 50 relevant messages:
"{query}"

The query should:

1. Be as simple as possible using correct schema and table references
2. Use appropriate JOINs and WHERE clauses to find relevant information.
3. Order results by relevance to the query
4. Return only non-null message text and date, in that order
5. Convert the message.date (stored as unix timestamp * 1000000000) to readable format
6. Select for a broad range of cases and meanings to help answer the query


Return ONLY the SQL query with no explanation or additional text."""

    response = requests.post(llm_endpoint, json={
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1024
    })

    result = response.json()["reply"].strip()

    pattern = r'```(.*?)```'

    match = re.search(pattern, result, re.DOTALL)
    if match:
        result = match.group(1)
    else:
        result = "select * from message limit 5;"

    if 'sql\n' in result[:10].lower():
            result = result[4:]
    
    return result.strip()

def is_valid_date(date_string, date_format="%Y-%m-%d %H:%M:%S"):
    try:
        datetime.strptime(date_string, date_format)
        return True
    except ValueError:
        return False

def filter_messages(messages: List[Tuple]) -> List[Message]:
    """Step 2: Filter and clean messages."""
    filtered_messages = []
    
    for text, date in messages:

        if not text or text.isspace():
            continue
            
        if text.startswith('Loved ') or text.startswith('Liked ') or text.startswith('Emphasized ') or text.startswith('Reacted ') or text.startswith('Laughed at '):
            continue
            
        if re.match(r'^https?://\S+$', text) or text.startswith('‎'):
            continue

        if not is_valid_date(date):
            date = '1993-08-15 23:40:09'
        
        filtered_messages.append(Message(
            date=datetime.strptime(date, "%Y-%m-%d %H:%M:%S"),
            text=text
        ))
    
    return filtered_messages

def rank_and_summarize(
    messages: List[Message], 
    original_query: str, 
    llm_endpoint: str = URL
) -> Dict:
    if not messages:
        return {"summary": "No relevant messages found.", "conversations": []}
    
    conversations_text = []
    for msg in messages:
        conv_text = "Text: " + msg.text + "\n" + f"\nDate: {msg.date.strftime('%Y-%m-%d %H:%M:%S')}\n"
        conversations_text.append(conv_text)
    
    response_format = {
        "ranked_conversations": [
            {"text": "conversation text", "similarity_score": 0.0}
        ],
        "summary": "overall summary"
    }

    convos = '\n---\n'.join(conversations_text[:20])

    prompt = f"""Given this query: "{original_query}"

Here are message exchanges to analyze:

{convos}

Please:
1. Rank the top 5 most relevant conversations by similarity to the query
2. Provide a brief summary of the key points from these conversations
3. Return the response in this exact JSON format:
{json.dumps(response_format, indent=2)}"""

    response = requests.post(llm_endpoint, json={
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1024
    })
    
    result = response.json()["reply"].strip()
    return result

def process_results(results: str):
    start_marker = "```json\n"
    if not 'json' in results[:10]: start_marker = "```\n"
    end_marker = "\n```"
    start_index = results.find(start_marker) + len(start_marker)
    end_index = results.find(end_marker)

    json_str = results[start_index:end_index]

    json_obj = {}

    try:
        json_obj = json.loads(json_str)
    except json.JSONDecodeError as e:
        print("Invalid JSON:", e)

    return json_obj

def query_messages(query: str, db_path: str = "chat.db") -> Dict:
    print("Generating query for '{prompt}'\n".format(prompt=query))

    schema = get_db_schema(db_path)
    sql_query = query_to_sql(query, schema)
    
    results = []
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute(sql_query)
        results = cursor.fetchall()
    except sqlite3.OperationalError:
        print("Error executing query")
        return
    conn.close()

    if not results: return
    print("Returned {number} messages".format(number=len(results)))

    print("\nFiltering messages\n")
    filtered_messages = filter_messages(results)
    print("Filtered down to {number} messages".format(number=len(filtered_messages)))

    if not len(filtered_messages) > 0: return

    final_results = rank_and_summarize(filtered_messages, query)
    result = process_results(final_results)
    
    return result

if __name__ == "__main__":
    questions = [
        "What did I say about my meeting next week?",
        "Find messages about my workout routine.",
        "When did I last mention a doctor's appointment?",
        "What did I discuss about an upcoming conference?",
        "Find any messages about a gift I bought.",
        "When was the last time I talked about a movie night?",
        "What did I say about my weekend plans?",
        "Find messages related to a family gathering.",
        "When did I last mention a work trip?",
        "What did I talk about regarding my New Year's resolutions?",
        "Find messages related to a home improvement project.",
        "What plans did I make for February?",
        "When did I last discuss meeting a friend?",
        "What did I say about a recent promotion?",
        "Find messages about a new job opportunity.",
        "When was the last time I mentioned a concert?",
        "What did I discuss about an upcoming wedding?",
        "Find any messages about a new book I wanted to read.",
        "When did I last talk about a recent health concern?",
        "What did I say about an upcoming work deadline?"
    ]

    random.shuffle(questions)
    total = len(questions)
    counter = 0

    for q in questions:
        print("--------------------------------------------------------------------------------")
        results = query_messages(q)

        if results:
            counter += 1
            print("\nSummary:")
            print(results['summary'])
            print("\nTop Conversations:")
            for conv in results['ranked_conversations']:
                print("\n" + "-"*50)
                print(f"Similarity Score: {conv['similarity_score']}")
                print(conv['text'])
            print("\n\n")
        print("--------------------------------------------------------------------------------")


    print("Score: {counter}/{total}".format(counter=counter, total=total))