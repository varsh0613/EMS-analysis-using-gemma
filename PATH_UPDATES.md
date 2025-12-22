# Path Updates - Migration to Relative Paths

All hardcoded file paths have been updated to use **relative paths** based on file location. This makes the codebase portable and independent of the user's folder structure.

## Files Updated

### 1. backend/main.py
**Before:**
```python
BASE_DIR = Path(r"C:\Users\SAHARA\OneDrive\Desktop\uni\gemma")
CSV_PATH = BASE_DIR / "eda" / "eda.csv"
```

**After:**
```python
BASE_DIR = Path(__file__).parent.parent  # Points to gemma root
CSV_PATH = BASE_DIR / "eda" / "eda.csv"
```

### 2. backend/geospatial/geospatial_engine.py
**Before:**
```python
df_incidents.to_csv(r"C:\Users\SAHARA\OneDrive\Desktop\uni\gemma\geospatial\incidents_with_h3.csv")
df = load_incidents(r"C:\Users\SAHARA\OneDrive\Desktop\uni\gemma\eda\eda.csv")
```

**After:**
```python
output_dir = Path(__file__).parent  # geospatial folder
df_incidents.to_csv(output_dir / "incidents_with_h3.csv")

eda_csv = Path(__file__).parent.parent / "eda" / "eda.csv"
df = load_incidents(str(eda_csv))
```

### 3. backend/op_efficiency/op_efficiency_pipeline.py
**Before:**
```python
EDA_CSV = Path(r"C:\Users\SAHARA\OneDrive\Desktop\uni\gemma\eda\eda.csv")
OUTPUT_DIR = Path(r"C:\Users\SAHARA\OneDrive\Desktop\uni\gemma\op_efficiency\outputs")
```

**After:**
```python
EDA_CSV = Path(__file__).parent.parent / "eda" / "eda.csv"
OUTPUT_DIR = Path(__file__).parent / "outputs"
```

### 4. backend/risk_score/risk_score_pipeline.py
**Before:**
```python
INPUT_CSV = r"C:\Users\SAHARA\OneDrive\Desktop\uni\gemma\eda\eda.csv"
OUT_DIR = r"C:\Users\SAHARA\OneDrive\Desktop\uni\gemma\risk_score\outputs"
```

**After:**
```python
INPUT_CSV = str(Path(__file__).parent.parent / "eda" / "eda.csv")
OUT_DIR = str(Path(__file__).parent / "outputs")
```

### 5. backend/risk_score/risk_by_location.py
**Before:**
```python
OUT_DIR = r"C:\Users\SAHARA\OneDrive\Desktop\uni\gemma\risk_score\outputs"
```

**After:**
```python
OUT_DIR = str(Path(__file__).parent / "outputs")
```

### 6. backend/op_efficiency/risk_by_hour_location.py
**Before:**
```python
EDA_CSV = Path(r"C:\Users\SAHARA\OneDrive\Desktop\uni\gemma\eda\eda.csv")
RISK_OUTPUTS = Path(r"C:\Users\SAHARA\OneDrive\Desktop\uni\gemma\risk_score\outputs")
OP_OUTPUT_DIR = Path(r"C:\Users\SAHARA\OneDrive\Desktop\uni\gemma\op_efficiency\outputs")
```

**After:**
```python
EDA_CSV = Path(__file__).parent.parent / "eda" / "eda.csv"
RISK_OUTPUTS = Path(__file__).parent.parent / "risk_score" / "outputs"
OP_OUTPUT_DIR = Path(__file__).parent / "outputs"
```

## How It Works

### Path Resolution Pattern

```
__file__ = current file location
Path(__file__).parent = folder containing current file
Path(__file__).parent.parent = parent folder of current file
```

### Examples

**From backend/main.py:**
- `__file__` = `backend/main.py`
- `Path(__file__).parent` = `backend/`
- `Path(__file__).parent.parent` = `gemma/` (root)

**From backend/op_efficiency/op_efficiency_pipeline.py:**
- `__file__` = `backend/op_efficiency/op_efficiency_pipeline.py`
- `Path(__file__).parent` = `backend/op_efficiency/`
- `Path(__file__).parent.parent` = `backend/`
- `Path(__file__).parent.parent.parent` = `gemma/` (root)

## Benefits

✓ **Portable**: Works regardless of where the project folder is located
✓ **Cross-platform**: Works on Windows, Mac, Linux
✓ **No hardcoding**: No user-specific paths in code
✓ **Flexible**: Can move the entire `gemma` folder anywhere and it still works

## Testing

Run any script to verify paths work:
```bash
python backend/main.py
python backend/op_efficiency/op_efficiency_pipeline.py
python backend/risk_score/risk_score_pipeline.py
```

All paths should resolve correctly relative to file locations.
