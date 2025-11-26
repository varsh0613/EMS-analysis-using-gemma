# code_executor.py
import traceback
import re
from typing import Optional, Tuple
import pandas as pd

PLACEHOLDER_PATTERN = re.compile(r"\bDataFrame\s*\(\s*\.\.\.\s*\)|\bpd\.DataFrame\s*\(\s*\.\.\.\s*\)", re.IGNORECASE)
IMPORT_PD_WRONG = re.compile(r"\bimport\s+pd\b", re.IGNORECASE)

class CodeExecutor:
    """
    Execute python code (string) where 'df' and 'pd' are available.
    Returns (cleaned_df, None) on success, or (None, traceback_str) on failure.
    """

    def _sanitize(self, code: str) -> Tuple[bool, str]:
        """
        Return (ok, message). If placeholder patterns found, return ok=False with message.
        Also fix accidental 'import pd' to 'import pandas as pd' to help model mistakes.
        """
        if IMPORT_PD_WRONG.search(code):
            code = IMPORT_PD_WRONG.sub("import pandas as pd", code)

        if PLACEHOLDER_PATTERN.search(code):
            return False, "Code contains placeholder DataFrame(...) calls (e.g., pd.DataFrame(...)). Remove placeholders and operate on existing df."

        return True, code

    def execute(self, df: pd.DataFrame, code: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        if not code or not code.strip():
            return None, "Empty code string"

        ok, sanitized_or_msg = self._sanitize(code)
        if not ok:
            return None, sanitized_or_msg

        # copy to avoid mutating original on failure
        local_vars = {"df": df.copy(), "pd": pd}

        try:
            exec(sanitized_or_msg, {}, local_vars)
            cleaned = local_vars.get("df", None)
            if cleaned is None or not isinstance(cleaned, pd.DataFrame):
                return None, "Executed code did not produce a pandas DataFrame named 'df'."
            return cleaned, None
        except Exception:
            return None, traceback.format_exc()
