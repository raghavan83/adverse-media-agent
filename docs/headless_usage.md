# Headless Usage

This version supports a browser-free execution mode for restricted notebook or DevCloud environments.

## Run
```bash
python run_screening.py --input input/request_adani.json --output-dir outputs
```

## What it writes
- `outputs/<CASE_ID>_result.json`
- `outputs/<CASE_ID>_summary.txt`
- `outputs/<CASE_ID>_agent_traces.json`
- `logs/app.log`

## Example flow
```bash
python run_screening.py --input input/request_adani.json --output-dir outputs
cat outputs/*_summary.txt
cat outputs/*_result.json | head -n 80
```

## Why use headless mode
- No browser required
- No port forwarding required
- Works in notebook terminals and remote shells
- Produces audit-friendly output artifacts


## Reuse loaded LLM
This version caches the LLM client in-process so it initializes once and is reused for subsequent requests handled by the same Python process.

### Single request with warm-up
```bash
python run_screening.py --input input/request_adani.json --output-dir outputs --warm-llm
```

### Batch requests in one process
```bash
python run_screening.py --input input/request_batch.json --output-dir outputs --warm-llm
```

Check `logs/app.log` for `reusing cached llm client` entries.
