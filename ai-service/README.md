# DevOps Copilot Lite AI Service

Run locally with Python 3.11+. On this machine Python 3.13 is installed but is
not registered with `py`, so use the setup script instead of `py -3.12`:

```powershell
.\setup.ps1
.\setup.ps1 -Serve
```

`setup.ps1` finds `Python313` under the current user's Local Programs folder,
creates an isolated `.venv`, installs the pinned dependencies, runs the tests
and evaluation, and starts FastAPI when `-Serve` is supplied. Use
`-SkipTests` only when you explicitly want to skip verification.

Call `POST /api/v1/analyze` with:

```json
{"log_content":"[ERROR] cannot find symbol", "source_type":"MAVEN"}
```

By default this service uses deterministic rules and safe Python static checks. To
enable optional Ollama enrichment for larger code models, set `OLLAMA_ENABLED=true`,
make sure Ollama is running, and set `OLLAMA_MODEL` to an installed code-capable
model. The integration sends line-numbered code context, uses deterministic model
sampling, and limits context with `OLLAMA_MAX_CODE_CHARACTERS` (default 60,000).
Any Ollama failure automatically returns the static/rule-based analysis instead.

Example local configuration before starting the service:

```powershell
$env:OLLAMA_ENABLED="true"
$env:OLLAMA_MODEL="your-installed-code-model"
$env:OLLAMA_MAX_CODE_CHARACTERS="60000"
.\setup.ps1 -Serve
```

## Run without Docker or FastAPI

The core rule engine uses only the Python standard library. From `ai-service/`:

```powershell
.\.venv\Scripts\python.exe run_analyzer.py datasets/sample-log.txt --source-type MAVEN
.\.venv\Scripts\python.exe evaluate.py
```

The analyzer now scores every applicable rule and uses `source_type` to resolve
ambiguous dependency failures, rather than returning the first regex match. It
also creates stable incident fingerprints when only line numbers or versions
change. `evaluate.py` calculates category accuracy against the labelled examples
in `datasets/evaluation_cases.jsonl`; this is a rule-engine benchmark, not a
claim of real-world LLM accuracy. Add held-out, anonymized production logs to
measure a meaningful project accuracy score.

Python source files also receive a safe static scan. It detects Python syntax
errors, undefined names, discarded recursive return values, constant
division/modulo-by-zero, literal index/key errors, invalid `int`/`float`
conversions, `len()` type errors, and `None` attribute access without executing
the uploaded code. It does not run uploaded files, so it cannot detect input-,
database-, network-, or installed-package-specific runtime failures.

## ML classifier: dataset, diagnostics, and calibration

The rule engine is the default and handles most known failures. The optional ML
classifier only runs when the rule engine returns `UNKNOWN`, and exists to catch
recurring failures specific to your own logs that no fixed regex will ever cover.

Three scripts support it, meant to be run in this order:

1. **`add_training_case.py`** - label a real log without hand-writing JSON:
   ```powershell
   .\.venv\Scripts\python.exe add_training_case.py --category PYTHON_MODULE --file snippet.log
   ```
   Prints running per-category counts so you know what's still thin.

2. **`diagnose_model.py`** - run *before* training to catch overfitting/underfitting.
   It fits the same pipeline `train_model.py` uses on a held-out split, cross-validates
   it, and prints a plain-language diagnosis (train/test gap, fold variance, a learning
   curve, and any category the model can never predict):
   ```powershell
   .\.venv\Scripts\python.exe diagnose_model.py --dataset datasets/training_cases.jsonl
   ```

3. **`train_model.py`** - fits `TfidfVectorizer(char n-grams) + CalibratedClassifierCV`
   on the full dataset and saves `models/log_classifier.joblib`. The classifier is
   wrapped in `CalibratedClassifierCV` rather than a raw `LogisticRegression`: with 9
   possible categories, raw `predict_proba` output under-states confidence even when the
   top prediction is correct, so an uncalibrated model can silently fail a confidence
   threshold it should have passed. `train_model.py` also prints a train/test sanity
   check and warns (without blocking) if it sees a large overfitting gap before saving.

4. **`evaluate_ml.py`** - the number that should actually decide `ML_ENABLED`. It runs
   the *saved* model against `datasets/evaluation_cases.jsonl` (never used in training)
   and compares it to the rule engine:
   ```powershell
   .\.venv\Scripts\python.exe evaluate_ml.py --model models/log_classifier.joblib
   ```

### Current results (included starter dataset + trained model)

This repo ships with `datasets/training_cases.jsonl` (193 examples across all 9
categories - a mix of hand-varied and template-generated placeholder logs, **not**
production data) and a model already trained and calibrated on it. Evaluated against
`datasets/evaluation_cases.jsonl` (18 held-out, human-written cases the model never
trained on):

| Metric | Before calibration | After calibration |
|---|---|---|
| ML raw top-1 accuracy | 100% | 100% |
| ML confident-and-correct (>= 60%) | 0% | 61.1% |
| Confident-and-wrong | 0% | 0% |

Before calibration, the model's predictions were always right but never confident
enough to clear the threshold, so `ML_ENABLED=true` did nothing in practice.
`CalibratedClassifierCV` fixed that without introducing any wrong predictions.

**Before relying on this for anything beyond a demo:** replace `training_cases.jsonl`
with real, anonymized logs from your own CI history (see `add_training_case.py`), then
re-run `diagnose_model.py` -> `train_model.py` -> `evaluate_ml.py` again. Placeholder
data is enough to prove the pipeline works end-to-end; it is not enough to trust the
model's judgment on logs it has never conceptually seen before.

To enable the trained model, set `ML_ENABLED=true` (see `.env.example`; this project
does not auto-load `.env`, so export the variable in your shell or set it before
starting `setup.ps1 -Serve`). ML only classifies logs the rule engine marks `UNKNOWN`,
and requires `ML_MINIMUM_CONFIDENCE` (default 60, tuned from the calibration run above)
before it will return an answer instead of deferring back to the rule engine's response.
