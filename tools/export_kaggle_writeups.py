"""Export complete manuscripts with public images pinned to an immutable commit."""
import argparse,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--asset-sha',required=True)
parser.add_argument('--output',type=Path,default=ROOT/'papers/kaggle')
options=parser.parse_args()
assert re.fullmatch('[0-9a-f]{40}',options.asset_sha)
options.output.mkdir(parents=True,exist_ok=True)
metadata={'status':'READY_NOT_SUBMITTED','competition':'gemma-4-developer-agent-paper','assets_commit':options.asset_sha,'writeups':[]}
for name in ['private-cache-witness.md','civil-time-guard.md']:
    source=ROOT/'papers'/name;text=source.read_text()
    assert '{{' not in text
    def replace(match):
        asset=match.group(2)
        assert (ROOT/'papers/assets'/asset).is_file()
        url='https://raw.githubusercontent.com/RayBerryHead/Gemma4-Contract-Repair/'+options.asset_sha+'/papers/assets/'+asset
        return '!['+match.group(1)+']('+url+')'
    exported=re.sub(r'!\[([^\]]*)\]\(assets/([^\)]+)\)',replace,text)
    words=len(exported.split());assert words<=3000
    file=options.output/name;file.write_text(exported)
    lines=text.splitlines()
    metadata['writeups'].append({'title':lines[0].removeprefix('# '),'subtitle':next(l.strip('*') for l in lines[1:] if l.startswith('*')),'file':name,'word_count_including_markdown_tables_captions_references':words,'sha256':hashlib.sha256(exported.encode()).hexdigest()})
(options.output/'submission-metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
print(json.dumps(metadata))
