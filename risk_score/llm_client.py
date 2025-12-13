# llm_client.py
import requests
import re
import time
from typing import List, Dict, Any, Optional

class LLMClient:
    """
    Stable Ollama client for Gemma 7B — optimized for:
    - cluster summarization
    - risk scoring pipelines
    - 100–200 sequential LLM calls without crashing
    """

    def __init__(
        self,
        model: str = "gemma:7b-instruct",
        base_url: str = "http://localhost:11434",
        timeout: int = 300,
        max_retries: int = 5,
        sleep_between_calls: float = 0.5,
    ):
        self.model = model
        self.base_url = base_url
        self.chat_url = f"{base_url}/api/chat"
        self.timeout = timeout
        self.max_retries = max_retries
        self.sleep_between_calls = sleep_between_calls
        self.session = requests.Session()

    # -------------------------------------------------------------------------
    # Internal Helper: Run HTTP post with retries
    # -------------------------------------------------------------------------
    def _post_with_retry(self, payload: Dict[str, Any]) -> Optional[Dict]:
        retries = self.max_retries
        delay = 1.0

        for attempt in range(1, retries + 1):
            try:
                resp = self.session.post(
                    self.chat_url,
                    json=payload,
                    timeout=self.timeout
                )
                resp.raise_for_status()
                return resp.json()

            except Exception as e:
                print(f"[LLMClient] Error (attempt {attempt}/{retries}): {e}")
                if attempt == retries:
                    print("[LLMClient] Max retries exceeded.")
                    return None
                time.sleep(delay)
                delay *= 2

        return None

    # -------------------------------------------------------------------------
    # Public: ask() → Free-form LLM response (text only)
    # -------------------------------------------------------------------------
    def ask(self, prompt: str) -> str:
        """
        Used for cluster-level risk summaries.
        Returns raw model text (no code extraction).
        """
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        }

        data = self._post_with_retry(payload)
        if not data:
            return ""

        # extract common fields from Ollama
        if "message" in data:
            return data["message"].get("content", "")
        if "response" in data:
            return data["response"]
        if "choices" in data:
            choice = data["choices"][0]
            if "message" in choice:
                return choice["message"].get("content", "")
            return choice.get("text", "")

        return str(data)

    # -------------------------------------------------------------------------
    # Public: chat_code() → Extract python code block from LLM output
    # (kept for compatibility but less used in risk pipeline)
    # -------------------------------------------------------------------------
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
            msg = data["choices"][0]
            if "message" in msg:
                text = msg["message"].get("content", "")
            else:
                text = msg.get("text", "")

        return self._extract_python_code(text)

    # -------------------------------------------------------------------------
    # Utility: Extract python code from LLM output
    # -------------------------------------------------------------------------
    def _extract_python_code(self, text: str) -> str:
        if not isinstance(text, str):
            return ""

        # Prefer ```python fenced blocks
        m = re.search(r"```python(.*?)```", text, re.DOTALL | re.IGNORECASE)
        if m:
            return m.group(1).strip()

        # Generic fenced block
        m = re.search(r"```(.*?)```", text, re.DOTALL)
        if m:
            return m.group(1).strip()

        return text.strip()

    # -------------------------------------------------------------------------
    # NEW: summarize_cluster() — Built for risk_score_pipeline
    # -------------------------------------------------------------------------
    def summarize_cluster(self, samples: List[Dict[str, Any]], cluster_id: int) -> str:
        """
        Summarize a cluster of EMS incidents and classify risk.
        This is the main workhorse for the risk scoring pipeline.
        """

        prompt = f"""
You are an EMS incident analysis expert.

Below are example incidents from cluster {cluster_id}.
Each contains time metrics (turnout, response, scene, cycle),
protocol used, primary impression, disposition, and transport details.

Your tasks:
1. Describe the type of incidents generally in this cluster.
2. Identify dominant operational patterns (fast/slow response, delays).
3. Identify clinical severity patterns (ALS/BLS, protocol severity).
4. Assign a final risk label: HIGH / MEDIUM / LOW.
5. Provide a concise explanation for the risk label.

Samples:
{samples}

Return a clean, human-readable summary. No code, no markdown fences.
"""

        text = self.ask(prompt)
        time.sleep(self.sleep_between_calls)
        return text
