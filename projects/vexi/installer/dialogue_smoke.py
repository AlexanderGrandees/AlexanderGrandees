"""Live local model evaluation with public synthetic prompts only; no microphone."""
import argparse
import json
from pathlib import Path
import sys
import time


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("runtime", type=Path); ap.add_argument("output", type=Path)
    args = ap.parse_args(); sys.path.insert(0, str(args.runtime.resolve()))
    from local_dialogue import LocalDialogue, UNAVAILABLE
    d = LocalDialogue({})
    rows = []
    for question in ("предложи два варианта отдыха дома", "второй подробнее", "без компьютера", "почему небо голубое", "объясни проще"):
        start = time.monotonic(); answer = d.answer(question)
        rows.append({"synthetic_public_question": question, "answer": answer,
                     "seconds": round(time.monotonic() - start, 2),
                     "transport_ok": bool(answer and answer != UNAVAILABLE and d.last_answer == answer)})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"model": "qwen3:4b-instruct-2507-q4_K_M", "rows": rows,
        "semantic_review": "PENDING", "microphone_field": "NOT_RUN"}, ensure_ascii=False, indent=2), "utf-8")
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    return 0 if all(r["transport_ok"] for r in rows) else 1


if __name__ == "__main__": raise SystemExit(main())
