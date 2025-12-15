# llm_client.py
import requests
import re
import time
from typing import List, Dict, Any, Optional


class LLMClient:
    """
    Gemma 7B client (rewritten for speed + correct mode switching)

    Fixes:
    - NO MORE: “No EMS data was provided…”
    - auto-detection between:
        1) General chat
        2) Data/Analysis/ML
        3) EMS operational assistant
    - Fast responses (<5–8s)
    - Low hallucinations
    """

    def __init__(
        self,
        model: str = "gemma:7b-instruct",
        base_url: str = "http://localhost:11434",
        timeout: int = 60,
        max_retries: int = 3,
        sleep_between_calls: float = 0.05,
    ):
        self.model = model
        self.base_url = base_url
        self.chat_url = f"{base_url}/api/chat"
        self.timeout = timeout
        self.max_retries = max_retries
        self.sleep_between_calls = sleep_between_calls
        self.session = requests.Session()

    # -------------------------------------------------------------------
    # Internal post with retry
    # -------------------------------------------------------------------
    def _post_with_retry(self, payload: Dict) -> Optional[Dict]:
        delay = 0.5
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = self.session.post(
                    self.chat_url, json=payload, timeout=self.timeout
                )
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                print(f"[LLMClient] Error {attempt}: {e}")
                if attempt == self.max_retries:
                    return None
                time.sleep(delay)
                delay *= 1.4
        return None

    # -------------------------------------------------------------------
    # MODE DETECTION (Dual-mode C)
    # -------------------------------------------------------------------
    def _build_system_prompt(self, user_message: str) -> str:
        msg = user_message.lower()

        # ----- MODE 1 — Data analysis -----
        data_keywords = [
            "dataset", "csv", "table", "incident count", "top city",
            "cluster", "kmeans", "model", "heatmap", "classification",
            "risk dashboard", "predict", "feature"
        ]
        if any(k in msg for k in data_keywords):
            return (
                "You are a data analysis assistant. "
                "Answer ONLY about data, statistics, ML, clusters, predictions, "
                "and quantitative insights. "
                "If the user asks about EMS symptoms, ignore — stay in data mode."
            )

        # ----- MODE 2 — EMS operational assistant (SAFE) -----
        ems_keywords = [
            "ems", "protocol", "patient", "breathing", "difficulty",
            "incident", "collapse", "risk", "seizure", "unresponsive",
            "chest pain"
        ]
        if any(k in msg for k in ems_keywords):
            return (
                "You are an EMS *operational* assistant. "
                "You DO NOT give medical treatment advice. "
                "You ONLY provide: \n"
                "- operational severity classification (LOW/MEDIUM/HIGH),\n"
                "- scene observations,\n"
                "- dispatch/transport priorities,\n"
                "- recommended EMS workflow steps.\n\n"
                "If the user does NOT provide patient details, "
                "still answer normally using general EMS operational knowledge. "
                "NEVER say 'No EMS data provided'. Just answer."
            )

        # ----- MODE 3 — General chat -----
        return (
            "You are a fast friendly conversational assistant. "
            "Keep responses short. Do NOT assume EMS or data mode unless asked."
        )

    # -------------------------------------------------------------------
    # Public ask()
    # -------------------------------------------------------------------
    def ask(self, prompt: str) -> str:
        system_prompt = self._build_system_prompt(prompt)

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "options": {
                "temperature": 0.2,
                "top_p": 0.85,
                "num_ctx": 4096,
                "num_predict": 2048
            }
        }

        data = self._post_with_retry(payload)
        if not data:
            return "I'm having trouble reaching the model right now."

        # Ollama formats vary
        if "message" in data:
            return data["message"].get("content", "")
        if "response" in data:
            return data["response"]
        if "choices" in data:
            c = data["choices"][0]
            if "message" in c:
                return c["message"].get("content", "")
            return c.get("text", "")

        return str(data)

    # -------------------------------------------------------------------
    # Code extractor
    # -------------------------------------------------------------------
    def chat_code(self, messages: List[Dict[str, str]]) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        data = self._post_with_retry(payload)
        if not data:
            return ""

        text = ""
        if "message" in data:
            text = data["message"].get("content", "")
        elif "response" in data:
            text = data["response"]
        elif "choices" in data:
            m = data["choices"][0]
            if "message" in m:
                text = m["message"].get("content", "")
            else:
                text = m.get("text", "")

        return self._extract_python_code(text)

    def _extract_python_code(self, text: str) -> str:
        if not isinstance(text, str):
            return ""
        m = re.search(r"```python(.*?)```", text, re.DOTALL | re.IGNORECASE)
        if m:
            return m.group(1).strip()
        m = re.search(r"```(.*?)```", text, re.DOTALL)
        if m:
            return m.group(1).strip()
        return text.strip()

    # -------------------------------------------------------------------
    # summarize_cluster()
    # -------------------------------------------------------------------
    def summarize_cluster(self, samples: List[Dict[str, Any]], cluster_id: int) -> str:

        prompt = f"""
Summarize EMS incidents from cluster {cluster_id}.

Include:
1. Common incident patterns
2. Operational patterns (time, location, delays)
3. Clinical presentation patterns (safe + general)
4. Operational severity category (LOW/MEDIUM/HIGH)
5. Short, readable output.

Samples:
{samples}
"""

        text = self.ask(prompt)
        time.sleep(self.sleep_between_calls)
        return text
