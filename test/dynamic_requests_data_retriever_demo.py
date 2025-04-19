import os
import uuid
import requests
from datetime import datetime

ROOT_LOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'LOGER', 'data_retriever')
os.makedirs(ROOT_LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(ROOT_LOG_DIR, "data_retriever_log.txt")

def log_action(task, message):
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"[{datetime.now()}] [{task}] {message}\n")
    print(f"[LOG] [{task}] {message}")

def unique_filename(task, ext):
    return os.path.join(ROOT_LOG_DIR, f"{task}_{uuid.uuid4().hex[:8]}.{ext}")

def fetch_github_api():
    task = "api_github"
    url = "https://api.github.com/repos/python/cpython"
    try:
        resp = requests.get(url, headers={"Accept": "application/vnd.github.v3+json"}, timeout=15)
        resp.raise_for_status()
        json_file = unique_filename(task, "json")
        with open(json_file, "w", encoding="utf-8") as f:
            f.write(resp.text)
        log_action(task, f"Fetched GitHub API {url} and saved to {json_file}")
    except Exception as e:
        log_action(task, f"ERROR: Failed to fetch {url}: {e}")

def fetch_stackoverflow():
    task = "web_stackoverflow"
    url = "https://stackoverflow.com/questions"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        html_file = unique_filename(task, "html")
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(resp.text)
        log_action(task, f"Fetched Stack Overflow page {url} and saved to {html_file}")
    except Exception as e:
        log_action(task, f"ERROR: Failed to fetch {url}: {e}")

def simulate_db_query():
    task = "db_simulated"
    query = "SELECT * FROM users WHERE id=1"
    # Simulate a DB result
    result = {"id": 1, "username": "testuser", "email": "test@example.com"}
    txt_file = unique_filename(task, "txt")
    with open(txt_file, "w", encoding="utf-8") as f:
        f.write(f"Query: {query}\nResult: {result}\n")
    log_action(task, f"Simulated DB query and saved to {txt_file}")

def error_demo():
    task = "error_missing_url"
    try:
        # Simulate missing URL error
        raise ValueError("No URL provided for API fetch!")
    except Exception as e:
        log_action(task, f"ERROR: {e}")

def main():
    fetch_github_api()
    fetch_stackoverflow()
    simulate_db_query()
    error_demo()

if __name__ == "__main__":
    main()
