# generator_agent.py
import textwrap

class GeneratorAgent:
    def __init__(self, llm_client):
        self.llm = llm_client

    def _system_message(self):
        return {
            "role": "system",
            "content": (
                "You are a precise Python pandas code generator. Return ONLY executable Python code, "
                "no markdown, no backticks, and no explanation text. The code will run in a sandbox "
                "where a pandas DataFrame named `df` is already provided. "
                "Do NOT create or replace df with pd.DataFrame(...). Do NOT use 'import pd'. "
                "If you need pandas, use the provided pd alias (pd is available). "
                "Follow these rules: check column existence before referencing (if 'col' in df.columns: ...), "
                "do not use inplace=True, prefer clear multi-line steps, coerce numerics with pd.to_numeric(..., errors='coerce'), "
                "normalize dates with pd.to_datetime(..., errors='coerce'), normalize NA-like strings to pd.NA, strip whitespace on string columns."
            )
        }

    def _initial_user_message(self, df, sample_rows=5):
        cols = list(df.columns)
        dtypes = df.dtypes.astype(str).to_dict()
        sample = df.head(sample_rows).to_csv(index=False)
        user_msg = textwrap.dedent(f"""
        Generate Python code that cleans the pandas DataFrame `df`.

        RULES (MUST FOLLOW):
        1) Return ONLY executable Python code. No backticks, no markdown, no explanation.
        2) Allowed columns: {cols}
        3) Column dtypes: {dtypes}
        4) After any renames you do, use only the new names.
        5) Always assign result back to df (e.g., df = df.drop_duplicates()).
        6) Do not use inplace=True.
        7) Normalize empty/NA-like strings ('', ' ', 'NA', 'N/A', 'None') to pd.NA.
        8) Coerce numeric columns with pd.to_numeric(..., errors='coerce').
        9) Normalize probable datetime columns using pd.to_datetime(..., errors='coerce').
        10) Strip whitespace for string columns before other transforms.
        11) Drop duplicates and obviously empty rows.
        12) Do not import pandas (pd is available).

        SAMPLE_ROWS (CSV):
        {sample}

        Provide only the Python code that modifies `df`.
        """).strip()
        return {"role": "user", "content": user_msg}

    def _repair_user_message(self, df, last_code: str, traceback: str, evaluator_notes: str, attempt:int):
        cols = list(df.columns)
        dtypes = df.dtypes.astype(str).to_dict()
        msg = textwrap.dedent(f"""
        Your previous code attempt (attempt {attempt}) failed or produced issues.

        COLUMNS: {cols}
        DTYPES: {dtypes}

        The code you attempted:
        {last_code}

        The Python traceback was:
        {traceback}

        Evaluator notes:
        {evaluator_notes}

        Fix the code accordingly. Follow the same rules as before. Return ONLY corrected Python code (no markdown, no backticks, no commentary).
        """).strip()
        return {"role": "user", "content": msg}

    def generate_initial(self, df):
        system = self._system_message()
        user = self._initial_user_message(df)
        return self.llm.chat([system, user])

    def generate_repair(self, df, last_code: str, traceback: str, evaluator_notes: str, attempt:int):
        system = self._system_message()
        user = self._repair_user_message(df, last_code, traceback, evaluator_notes, attempt)
        return self.llm.chat([system, user])
