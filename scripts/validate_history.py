"""Primera validación financiera; un FAIL deja el resultado guardado y retorna 2."""
import json
from pathlib import Path

from fondoclaro.finance.golden import save_evaluation
from fondoclaro.serialization import canonical

root=Path.cwd()
result=save_evaluation(root)
summary={key:value for key,value in result.items() if key!="comparisons"}
print(json.dumps(json.loads(canonical(summary)),ensure_ascii=False,indent=2))
print("Resultado completo: reports/golden_validation/result.json")
raise SystemExit(0 if result["status"]=="PASS" else 2)
