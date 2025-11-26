# controller.py
import os
import time
import sys
import json
from datetime import datetime
import pandas as pd

from llm_client import LLMClient
from generator_agent import GeneratorAgent
from gemma.cleaning.code_executor import CodeExecutor

# ================== CONFIG ==================
# Edit these if needed
INPUT_CSV = "C:\\Users\\SAHARA\\Downloads\\Emergency_Medical_Service_(EMS)_Incidents_20251121.csv"
OUTPUT_CSV = "C:\\Users\\SAHARA\\Downloads\\cleaned_ems_output2.csv"
MODEL_NAME = "gemma:7b-instruct"
ATTEMPT_DIR = "./attempts"
LOG_PATH = "run_log.txt"
FINAL_CODE_PATH = "final_code.py"
MAX_ATTEMPTS = 10
SCORE_THRESHOLD = 8   # basic evaluator threshold (0-10)
PAUSE_SECONDS = 1.5
# ============================================

os.makedirs(ATTEMPT_DIR, exist_ok=True)

def log(msg: str, print_console=True):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    if print_console:
        print(line)

def evaluator_basic(original_df: pd.DataFrame, cleaned_df: pd.DataFrame):
    """Simple deterministic checks to decide if cleaning progressed.""" 
    notes = []
    score = 10

    if not isinstance(cleaned_df, pd.DataFrame):
        return 0, "Result is not a DataFrame."

    orig_cols = set(original_df.columns)
    new_cols = set(cleaned_df.columns)
    lost = orig_cols - new_cols
    if len(lost) > max(1, len(orig_cols) * 0.25):
        notes.append(f"Many columns removed: {list(lost)[:8]}")
        score -= 3

    try:
        if cleaned_df.duplicated().mean() > original_df.duplicated().mean() + 0.001:
            notes.append("Duplicates increased after cleaning.")
            score -= 1
    except Exception:
        notes.append("Could not evaluate duplicates.")
        score -= 1

    try:
        obj_cols = [c for c in cleaned_df.columns if cleaned_df[c].dtype == "object"]
        trim_issues = []
        for c in obj_cols[:6]:
            s = cleaned_df[c].astype(str)
            pct = (s.str.startswith(" ") | s.str.endswith(" ")).mean()
            if pct > 0.05:
                trim_issues.append((c, float(pct)))
        if trim_issues:
            notes.append(f"Trim issues: {trim_issues}")
            score -= 1
    except Exception:
        pass

    score = max(0, min(10, score))
    return score, ("\n".join(notes) if notes else "Basic checks passed.")

def df_info(df: pd.DataFrame, sample_rows=5):
    """Return minimal context about dataframe to feed back to LLM."""
    return {
        "columns": list(df.columns),
        "dtypes": df.dtypes.astype(str).to_dict(),
        "head_csv": df.head(sample_rows).to_csv(index=False)
    }

def controller_loop(input_csv=INPUT_CSV, output_csv=OUTPUT_CSV):
    if not os.path.exists(input_csv):
        log(f"ERROR: Input CSV not found: {input_csv}")
        sys.exit(1)

    log("Loading dataset...")
    df_orig = pd.read_csv(input_csv, low_memory=False)
    log(f"Loaded dataframe: {len(df_orig)} rows x {len(df_orig.columns)} cols")

    llm = LLMClient(model=MODEL_NAME, base_url="http://localhost:11434", timeout=300, max_retries=3)
    gen = GeneratorAgent(llm)
    execer = CodeExecutor()

    prev_code = None
    prev_error = None

    # initial request
    code = gen.generate_initial(df_orig)

    for attempt in range(1, MAX_ATTEMPTS + 1):
        log(f"ATTEMPT {attempt} ---------------------------")
        # save attempted code
        attempt_path = os.path.join(ATTEMPT_DIR, f"attempt_{attempt}.py")
        with open(attempt_path, "w", encoding="utf-8") as f:
            f.write("# Attempted code (may be empty)\n")
            f.write(code or "# <empty>")

        if not code or not code.strip():
            log("Generator returned empty code. Regenerating initial code.")
            time.sleep(PAUSE_SECONDS)
            code = gen.generate_initial(df_orig)
            continue

        # quick safety check: refuse to run code that creates a placeholder DataFrame or 'import pd'
        if "pd.DataFrame(...)" in code or "DataFrame(...)" in code and "pd.DataFrame" in code:
            log("Detected placeholder DataFrame(...) in code; asking generator to remove placeholders.")
            prev_code = code
            prev_error = "Detected placeholder DataFrame(...) in code; remove placeholder and operate on existing df."
            code = gen.generate_repair(df_orig, prev_code, prev_error, "Placeholder removed", attempt)
            time.sleep(PAUSE_SECONDS)
            continue

        log("Executing code (preview):")
        log(code[:1500] + ("\n... (truncated)" if len(code) > 1500 else ""))

        cleaned_df, err = execer.execute(df_orig, code)

        if err is None:
            score, notes = evaluator_basic(df_orig, cleaned_df)
            log(f"Evaluator score: {score}/10")
            log(f"Evaluator notes: {notes}")

            if score >= SCORE_THRESHOLD:
                log("Threshold satisfied. Saving outputs...")

                # Save cleaned csv
                cleaned_df.to_csv(output_csv, index=False)
                log(f"Saved cleaned CSV → {output_csv}")

                # Save final code
                with open(FINAL_CODE_PATH, "w", encoding="utf-8") as f:
                    f.write(code)
                log(f"Saved final working code → {FINAL_CODE_PATH}")

                # Save metadata
                meta = {
                    "input": os.path.abspath(input_csv),
                    "output": os.path.abspath(output_csv),
                    "model": MODEL_NAME,
                    "attempts": attempt,
                    "score": score,
                    "timestamp": datetime.now().isoformat()
                }
                with open(os.path.join(ATTEMPT_DIR, "meta.json"), "w", encoding="utf-8") as f:
                    json.dump(meta, f, indent=2)
                log("Run completed successfully.")
                return cleaned_df

            # if not enough, ask for repair guided by evaluator notes
            log("Score below threshold; requesting repair from generator.")
            prev_code = code
            prev_error = "No runtime error but failed evaluator checks."
            code = gen.generate_repair(df_orig, prev_code, prev_error, notes, attempt)
            time.sleep(PAUSE_SECONDS)
            continue

        else:
            # runtime error: send traceback and previous code back
            log("Runtime error occurred during execution. Traceback (truncated):")
            log(err[:4000])
            prev_code = code
            prev_error = err
            code = gen.generate_repair(df_orig, prev_code, prev_error, "Runtime error in execution", attempt)
            time.sleep(PAUSE_SECONDS)
            continue

    # failed after attempts
    log("Reached maximum attempts without success.")
    # save last failed code and original csv for debugging
    failed_code_path = os.path.join(ATTEMPT_DIR, "last_failed_code.py")
    with open(failed_code_path, "w", encoding="utf-8") as f:
        f.write(code or "# empty")
    fallback = output_csv.replace(".csv", "_FAILED.csv")
    df_orig.to_csv(fallback, index=False)
    log(f"Saved original dataframe to {fallback} and last code to {failed_code_path}")
    raise RuntimeError("Cleaning failed after maximum attempts.")

if __name__ == "__main__":
    controller_loop()
