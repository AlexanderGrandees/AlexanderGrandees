import json
from pathlib import Path
p = Path(__file__).resolve().parent / "config.json"
d = json.loads(p.read_text(encoding="utf-8"))
print("Текущий Silero voice:", d.get("silero_speaker", "xenia"))
print("1 = xenia")
print("2 = baya")
choice = input("Выбор: ").strip()
if choice == "2":
    d["silero_speaker"] = "baya"
else:
    d["silero_speaker"] = "xenia"
p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
print("Готово:", d["silero_speaker"])
