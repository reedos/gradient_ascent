"""Build deterministic, self-contained teaching kits from the same data the site renders."""
from pathlib import Path
import json
import zipfile

ROOT=Path(__file__).resolve().parent.parent
SOURCE=ROOT/'examples/practical_labs'
DEST=ROOT/'site/public/downloads/practical-labs'
DEST.mkdir(parents=True,exist_ok=True)
cases=json.loads((SOURCE/'cases.json').read_text(encoding='utf-8'))
for c in cases:
    readme=f'''# {c['title']}

Python 3.10 or newer. Standard library only; no pip installation.
All source records are synthetic. Replay is authored playback, not a model benchmark.

## Start without a model

Unzip the archive, open a terminal in the extracted directory, and run:

    python run.py {c['id']} --mode replay
    python -m unittest discover -s . -p test_labs.py -v

The archive contains all six cases because they share the runner and boundary tests.
The title above identifies the suggested starting case.

## Run your own model

With Ollama already running and your chosen model installed:

    python run.py {c['id']} --mode live --backend ollama --model YOUR_MODEL

Replace YOUR_MODEL with the exact model name from `ollama list`.
For a compatible Chat Completions endpoint:

    python run.py {c['id']} --mode live --backend compatible --model YOUR_MODEL --base-url https://YOUR_HOST/v1

Set MODEL_API_KEY in your shell if the endpoint requires it. Never put the key in a prompt.
For PowerShell: $env:MODEL_API_KEY = 'your-key'
For bash/zsh: export MODEL_API_KEY='your-key'
Remote live mode sends the supplied records to that endpoint and may incur provider charges.
Compatibility varies: this runner uses messages, max_tokens, and non-streaming responses.
The Ollama adapter supplies a native JSON schema. Compatible endpoints use prompt-based JSON
and post-generation validation; native structured output support is not assumed there.
The agent uses a JSON decision protocol, not provider-native tool calling.
Use a dedicated compatible endpoint or adapt Model.__call__ for another provider API.

## What you are building

{c['summary']}

Use case: {c['use']}

Task: {c['task']}

'''+ '\n\n'.join(f'### {i+1}. {title}\n\n{body}' for i,(title,body) in enumerate(c['steps']))+f'''

## Check the result

'''+ '\n'.join('- '+r for r in c['rubric'])+f'''

Automated checks cover structure and selected control invariants, not all factual correctness.
For an actual model comparison, run multiple trials on a fixed held-out dataset and record
model/version, prompt, configuration, latency, token use, and human-reviewed failures.
The included authored expected response is a teaching reference, not a measured model result.

## Break it on purpose

{c['failure']}

## Adapt it

{c['adapt']}

Edit cases.json for data and instructions. Update validate() in run.py where fixture-specific
checks are deliberate. Change the tests and expected reference when you change the contract.
Do not "fix" a failing model result by weakening a check you still need.

## Important boundary

{c['nuance']}

{c['limits']}

The monitor creates lab-state-replay.sqlite or lab-state-live.sqlite in the current directory.
Use --state PATH for an independent experiment. A repeated event returns its recorded draft;
use a fresh state path when comparing changed prompts or models.
No email, calendar, purchase, shell, or production action is connected.

## Files

- run.py: model adapters, deterministic checks, bounded loop, SQLite outbox
- cases.json: six editable source packets, prompts, expected responses, review rubrics
- test_labs.py: offline boundary and integration tests
- prompt.txt: the selected task instructions
- sources.json: the selected synthetic input records
- expected.json: authored teaching response, not live output

Source project: https://github.com/reedos/gradient_ascent
'''
    files={'README.md':readme,'prompt.txt':c['prompt'],'sources.json':json.dumps(c['data'],indent=2),'expected.json':json.dumps(c['expected'],indent=2)}
    files.update({name:(SOURCE/name).read_text(encoding='utf-8') for name in ['run.py','cases.json','test_labs.py']})
    with zipfile.ZipFile(DEST/(c['id']+'.zip'),'w',zipfile.ZIP_DEFLATED) as archive:
        for name,body in sorted(files.items()):
            info=zipfile.ZipInfo(name,date_time=(2026,9,20,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(info,body.encode('utf-8'))
print(f'Packaged {len(cases)} practical labs')
records=[]
for path in sorted((SOURCE/'validation').rglob('*.json')):
    records.append({'record_path':str(path.relative_to(SOURCE/'validation')).replace('\\','/'),**json.loads(path.read_text(encoding='utf-8'))})
report=DEST.parent/'quality-validation.json'
report.write_text(json.dumps({'scope':'Development smoke trials using synthetic records, not a benchmark. Earlier failed trials are retained.','records':records},indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
(DEST.parent/'quality-prototype-notes.md').write_text((ROOT/'docs/QUALITY_PROTOTYPE.md').read_text(encoding='utf-8'),encoding='utf-8')
