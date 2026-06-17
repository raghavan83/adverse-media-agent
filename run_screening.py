import argparse
import json
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

from backend.db import Base, engine
from backend.models import ScreenRequest
from backend.pipeline import run_screening
from backend.logging_config import configure_logging

configure_logging()
Base.metadata.create_all(bind=engine)


def main():
    parser = argparse.ArgumentParser(description="Headless adverse media screening runner")
    parser.add_argument("--input", required=True, help="Path to request JSON file")
    parser.add_argument("--output-dir", default="outputs", help="Directory to write result files")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = BASE_DIR / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    payload = json.loads(input_path.read_text())
    request = ScreenRequest(**payload)
    result = run_screening(request)
    case_id = result["screening_case_id"]

    result_path = output_dir / f"{case_id}_result.json"
    summary_path = output_dir / f"{case_id}_summary.txt"
    audit_path = output_dir / f"{case_id}_agent_traces.json"

    result_path.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    summary_path.write_text(result.get("summary", ""), encoding="utf-8")
    audit_path.write_text(json.dumps(result.get("agent_traces", []), indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps({
        "screening_case_id": case_id,
        "result_file": str(result_path),
        "summary_file": str(summary_path),
        "agent_traces_file": str(audit_path),
        "risk_label": result.get("risk_label"),
        "risk_score": result.get("risk_score"),
        "retrieval_provider": result.get("retrieval_provider"),
    }, indent=2))


if __name__ == "__main__":
    main()
