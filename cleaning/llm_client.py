# llm_client.py
import requests
import re
import time

def extract_python_code(text: str) -> str:
    """Extract likely python code from model output (strip fences, surrounding quotes, comment-only lines)."""
    if not isinstance(text, str):
        return ""

    # 1) prefer explicit python fenced block
    m = re.search(r"```python(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if m:
        text = m.group(1)
    else:
        m = re.search(r"```(.*?)```", text, re.DOTALL)
        if m:
            text = m.group(1)

    # 2) remove leading/trailing quotes
    text = text.strip().strip('"').strip("'").strip()

    # 3) remove pure-comment lines (keep inline comments)
    lines = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("#") and len(s) < 300:
            continue
        lines.append(line)
    return "\n".join(lines).strip()

class LLMClient:
    def __init__(self, model="gemma:7b-instruct", base_url="http://localhost:11434", timeout=300, max_retries=3):
        self.model = model
        self.chat_url = f"{base_url}/api/chat"
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()

    def chat(self, messages):
        """
        messages: list of {"role": "system|user|assistant", "content": "..." }
        Returns extracted python code (string) or empty string on failure.
        Retries on transient errors with exponential backoff.
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False
        }

        backoff = 1.0
        for attempt in range(1, self.max_retries + 1):
            try:
                r = self.session.post(self.chat_url, json=payload, timeout=self.timeout)
                r.raise_for_status()
                data = r.json()
            except requests.exceptions.RequestException as e:
                print(f"LLM request failed (attempt {attempt}/{self.max_retries}): {e}")
                if attempt == self.max_retries:
                    return ""
                time.sleep(backoff)
                backoff *= 2.0
                continue
            except Exception as e:
                print(f"LLM unexpected error: {e}")
                return ""

            # parse common shapes returned by Ollama /api/chat
            text = ""
            if isinstance(data, dict):
                if "message" in data and isinstance(data["message"], dict):
                    text = data["message"].get("content", "")
                elif "response" in data:
                    text = data.get("response", "")
                elif "choices" in data and isinstance(data["choices"], list) and data["choices"]:
                    ch = data["choices"][0]
                    if isinstance(ch, dict) and "message" in ch:
                        text = ch["message"].get("content", "")
                    else:
                        text = ch.get("text", "")
                else:
                    text = str(data)
            else:
                text = str(data)

            code = extract_python_code(text)
            return code

        return ""
