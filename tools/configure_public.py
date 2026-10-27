"""Set machine-local execution paths without changing research settings."""
import argparse,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--artifact-root',type=Path,default=ROOT/'artifacts')
options=parser.parse_args()
if not (Path(sys.prefix)/'conda-meta').is_dir():raise SystemExit('Use a conda Python environment.')
path=ROOT/'configs/runtime.free.json'
config=json.loads(path.read_text())
config.update(artifact_root=str(options.artifact_root.resolve()),python=sys.executable,
              project_id=os.environ.get('GOOGLE_CLOUD_PROJECT','YOUR_GCP_PROJECT_ID'))
path.write_text(json.dumps(config,indent=2)+'\n')
print(json.dumps({'artifact_root':config['artifact_root'],'python':config['python'],'paid_fallback_enabled':config['paid_fallback_enabled']}))
