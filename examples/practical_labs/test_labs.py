"""Deterministic integration and boundary checks; not model-quality evaluations."""
import copy
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from unittest.mock import patch
from run import CASES, Model, approval_gate, digest, durable_once, json_object, replayer, retrieve, run_case, validate


class PracticalLabs(unittest.TestCase):
    def test_every_replay_runs_through_real_control_code(self):
        with tempfile.TemporaryDirectory() as folder:
            for slug in CASES:
                with self.subTest(slug=slug):
                    result = run_case(slug, replayer(slug), str(Path(folder)/'state.sqlite'))
                    self.assertNotEqual(result['status'], 'budget_exhausted')
                    self.assertTrue(result['output'])

    def test_retrieval_prefers_applicable_document_but_does_not_filter_by_date(self):
        c = CASES['evidence-answer']
        docs = retrieve(c['task'], c['data'])
        self.assertEqual(docs[0]['id'], 'policy-2026')
        self.assertIn('policy-old', [d['id'] for d in docs])

    def test_citation_not_in_context_fails(self):
        output = copy.deepcopy(CASES['evidence-answer']['expected'])
        with self.assertRaisesRegex(ValueError,'supplied evidence'):
            validate('evidence-answer', output, ['policy-old'])

    def test_internal_arithmetic_and_null_handling(self):
        output = copy.deepcopy(CASES['invoice-extraction']['expected'])
        output['computed_total_cents'] = 55000
        with self.assertRaisesRegex(ValueError,'Computed total'):
            validate('invoice-extraction', output)
        output = copy.deepcopy(CASES['invoice-extraction']['expected'])
        output['due_date'] = '2026-10-02'
        with self.assertRaisesRegex(ValueError,'due date'):
            validate('invoice-extraction', output)

    def test_workflow_stops_before_draft_on_missing_source(self):
        calls = []
        def ask(messages):
            calls.append(messages)
            output = copy.deepcopy(CASES['status-workflow']['expected'])
            output['items'].pop()
            return output
        with self.assertRaisesRegex(ValueError,'per source'):
            run_case('status-workflow', ask)
        self.assertEqual(len(calls),1)

    def test_workflow_drafts_from_checked_table_only(self):
        calls = []
        def ask(messages):
            calls.append(messages)
            return CASES['status-workflow']['expected'] if len(calls)==1 else {'summary':'A reviewed draft'}
        result = run_case('status-workflow', ask)
        self.assertEqual(result['output']['summary'],'A reviewed draft')
        self.assertEqual(set(json.loads(calls[1][1]['content'])), {'items','unknowns'})

    def test_approval_expiry_version_payload_and_duplicates(self):
        proposal = copy.deepcopy(CASES['approval-gate']['expected'])
        approval = {'digest':digest(proposal),'expires_at':200}
        receipts = set()
        self.assertIn('local receipt', approval_gate(proposal,approval,4,100,receipts))
        self.assertEqual(approval_gate(proposal,approval,4,100,receipts),'already recorded')
        for a,v,t in [({'digest':'wrong','expires_at':200},4,100),(approval,5,100),(approval,4,201)]:
            with self.subTest(a=a,v=v,t=t),self.assertRaises(ValueError):
                approval_gate(proposal,a,v,t,set())
        proposal['participant']='someone-else@example.test'
        with self.assertRaises(ValueError):
            approval_gate(proposal,approval,4,100,set())

    def test_unknown_tool_is_refused(self):
        with self.assertRaisesRegex(ValueError,'allowlist'):
            run_case('incident-agent', lambda _: {'decision':'tool','tool':'rollback'})

    def test_extra_tool_arguments_are_refused(self):
        with self.assertRaisesRegex(ValueError,'arbitrary arguments'):
            run_case('incident-agent', lambda _: {'decision':'tool','tool':'metrics','arguments':{'url':'anything'}})

    def test_agent_cannot_cite_unread_tool(self):
        with self.assertRaisesRegex(ValueError,'actually read'):
            run_case('incident-agent', lambda _: {**CASES['incident-agent']['expected'],'tool':''})

    def test_loop_exhausts_budget_without_success(self):
        result=run_case('incident-agent', lambda _: {'decision':'tool','tool':'metrics'})
        self.assertEqual(result['status'],'budget_exhausted')
        self.assertEqual(result['model_calls'],6)
        self.assertIsNone(result['output'])

    def test_durable_state_survives_reopen_and_skips_duplicate_generation(self):
        calls=[]
        def produce():
            calls.append(1)
            return {'draft':'Synthetic draft'}
        with tempfile.TemporaryDirectory() as folder:
            db=str(Path(folder)/'state.sqlite')
            durable_once(db,'event-1',produce)
            self.assertEqual(durable_once(db,'event-1',produce)['status'],'already_recorded')
            durable_once(db,'event-2',produce)
            with closing(sqlite3.connect(db)) as con:
                self.assertEqual(con.execute('SELECT count(*) FROM outbox').fetchone()[0],2)
        self.assertEqual(len(calls),2)

    def test_failed_generation_leaves_no_success_receipt(self):
        def fail():
            raise ValueError('provider failed')
        with tempfile.TemporaryDirectory() as folder:
            db=str(Path(folder)/'state.sqlite')
            with self.assertRaises(ValueError):
                durable_once(db,'event',fail)
            self.assertEqual(durable_once(db,'event',lambda:{'draft':'retry'})['status'],'pending_review')

    def test_live_mode_needs_explicit_model_and_secure_endpoint(self):
        for model,url in [(None,None),('chosen','http://external.example/v1'),('chosen','https://user:secret@example.test/v1')]:
            with self.assertRaises(ValueError):
                Model('compatible',model,url)

    def test_prose_and_markdown_fences_do_not_silently_pass_as_json(self):
        for text in ['[]','```json\n{}\n```','Here is the answer: {}']:
            with self.assertRaises(ValueError):
                json_object(text)

    def test_http_adapters_send_expected_contract_and_parse_responses(self):
        requests=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):
                pass
            def do_POST(self):
                payload=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                requests.append((self.path,payload,self.headers.get('Authorization')))
                reply={'message':{'content':'{"answer":"test"}'},'done_reason':'stop'} if self.path=='/api/chat' else {'choices':[{'message':{'content':'{"answer":"test"}'},'finish_reason':'stop'}]}
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps(reply).encode())
        with ThreadingHTTPServer(('127.0.0.1',0),Handler) as server:
            worker=Thread(target=server.serve_forever,daemon=True);worker.start()
            try:
                base=f'http://127.0.0.1:{server.server_port}'
                schema={'type':'object','properties':{'answer':{'type':'string'}},'required':['answer']}
                for backend in ('ollama','compatible'):
                    with patch.dict('os.environ',{'MODEL_API_KEY':'test-only-key'}):
                        model=Model(backend,'fixture',base if backend=='ollama' else base+'/v1')
                        self.assertEqual(model([{'role':'user','content':'test'}],schema),{'answer':'test'})
                self.assertEqual(requests[0][0],'/api/chat')
                self.assertEqual(requests[0][1]['format'],schema)
                self.assertFalse(requests[0][1]['stream'])
                self.assertIsNone(requests[0][2])
                self.assertEqual(requests[1][0],'/v1/chat/completions')
                self.assertEqual(requests[1][2],'Bearer test-only-key')
            finally:
                server.shutdown();worker.join()


if __name__=='__main__':
    unittest.main()
