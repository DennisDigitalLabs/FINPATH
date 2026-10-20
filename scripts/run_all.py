from pathlib import Path
import subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
for cmd in [[sys.executable,'scripts/run_eda.py'],[sys.executable,'scripts/train_pipeline.py'],[sys.executable,'scripts/generate_evidence.py'],[sys.executable,'scripts/generate_model_evidence.py'],[sys.executable,'scripts/generate_shap_evidence.py'],[sys.executable,'-m','pytest','-q']]:
 print('RUN:', ' '.join(map(str,cmd))); subprocess.run(cmd,cwd=ROOT,check=True)
