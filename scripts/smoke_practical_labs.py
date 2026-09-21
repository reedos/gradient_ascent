"""Record one synthetic live Ollama trial per lab; this is not a quality benchmark."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import sys
import tempfile
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'examples/practical_labs'))
from run import CASES, Model, run_case

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--model',required=True)
parser.add_argument('--case',choices=CASES)
parser.add_argument('--out',required=True,help='New directory for records; existing output is not overwritten.')
args=parser.parse_args()
out=Path(args.out);out.mkdir(parents=True,exist_ok=False)
failed=False
with tempfile.TemporaryDirectory() as folder:
    for slug in ([args.case] if args.case else CASES):
        model=Model('ollama',args.model,None)
        try:
            result=run_case(slug,model,str(Path(folder)/'state.sqlite'))
        except Exception as error:
            result={'status':'stopped','error':str(error)}
        record={'case':slug,'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'model':model.model,'backend':'ollama','mode':'live','synthetic_inputs':True,'trials':1,'prompt_sha256':hashlib.sha256(CASES[slug]['prompt'].encode()).hexdigest(),'runner_sha256':hashlib.sha256((ROOT/'examples/practical_labs/run.py').read_bytes()).hexdigest(),'request_metrics':model.trace,'returned_objects':model.outputs,**result}
        (out/(slug+'.json')).write_text(json.dumps(record,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        print(slug,result['status'],round(sum(x['elapsed_seconds'] for x in model.trace),2),flush=True)
        failed |= result['status'] in ('stopped','budget_exhausted')
raise SystemExit(1 if failed else 0)
