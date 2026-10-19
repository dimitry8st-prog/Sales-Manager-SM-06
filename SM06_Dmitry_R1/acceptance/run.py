"""Frozen SM06 acceptance runner. cp0 validates reference; cp1 needs candidate."""
import sys, json, copy, unittest, importlib.util
from pathlib import Path
from datetime import datetime
P=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(P/'candidate'),str(P/'reference')]
BASE=['tests/test_first_binding.py','tests/test_language_registry.py','tests/wave3/test_f120.py','tests/wave4/test_f122.py','tests/f130/tests/test_public.py','tests/f130/tests/test_candidate_f130.py']
def baseline():
 import subprocess, os
 ok=True
 for path in BASE:
  code="import sys,unittest,importlib.util;sys.path.insert(0,sys.argv[1]);s=importlib.util.spec_from_file_location('baseline',sys.argv[2]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(m));raise SystemExit(0 if r.wasSuccessful() and r.testsRun>0 and not r.skipped else 1)"
  r=subprocess.run([sys.executable,'-c',code,str(P/'reference'),str(P/'reference'/path)])
  ok=ok and r.returncode==0
 return ok
if len(sys.argv)!=2 or sys.argv[1] not in ['cp0','cp1']:raise SystemExit('usage: python acceptance/run.py cp0|cp1')
if sys.argv[1]=='cp0':raise SystemExit(0 if baseline() else 1)
if not (P/'candidate/first_sm06_language.py').exists():print('MISSING_IMPLEMENTATION');raise SystemExit(3)
import first_sm06_language as impl
from sales_language_registry import load_language_registry,LanguageRegistryError
from sales_runtime_materialization import prepare_bound_materials
from sales_rules import RuleViolation
from sales_action_locale import ActionLocaleError
from sales_first_binding import FirstBindingError
LOCALES=['en-GB','ru-RU','es-ES','da-DK','uk-UA']
FIELDS=['explicit_recipient_preference','substantive_reply_language','verified_company_business_language']
KINDS={'initial':'INITIAL','question':'QUESTION','objection':'OBJECTION','followup':'FOLLOWUP','handoff':'HANDOFF'}
class Acceptance(unittest.TestCase):
 def setup(self):
  f=json.loads((P/'reference/tests/f130/fixtures/runtime_initial_en.json').read_text())
  packs=[json.loads((P/'candidate/packs'/f'{locale}.json').read_text()) for locale in LOCALES]
  versions={x['locale']:x['version'] for x in packs}
  registry={'schema_version':'FIRST_LANGUAGE_REGISTRY_V1','registry_version':'sm06-test-v1','default_locale':'en-GB','active_locales':LOCALES[:],'language_pack_versions':versions}
  loaded=load_language_registry(registry,packs,approved_fact_ids=[])
  b=f['binding_config'];b['allowed_locales']=LOCALES[:];b['language_pack_versions']=versions
  return loaded,b,datetime.fromisoformat(f['now']),dict.fromkeys(FIELDS)
 def sel(self,l,b,n,e):return impl.select_language(l,b,now=n,evidence=e)
 def prep(self,l,b,n,e,t='initial',pin=None,save=None):
  return impl.prepare_language_materials(l,b,now=n,evidence=e,required_template_id=t,pinned_pack_version=pin,save_materials=save)
 def test_pack_shape_all5_kinds_and_no_fact_claim_ids(self):
  l,b,n,e=self.setup()
  for locale in LOCALES:
   pack=l['packs_by_locale'][locale];self.assertEqual(set(pack['templates']),set(KINDS))
   for id,kind in KINDS.items():
    t=pack['templates'][id];self.assertEqual(t['kind'],kind);self.assertEqual(t['fact_ids'],[]);self.assertTrue(t['subject'].strip());self.assertTrue(t['body'].strip())
 def test_all25_actual_chain_exact_once_immutable(self):
  l,b,n,e=self.setup()
  for locale in LOCALES:
   for t in KINDS:
    with self.subTest(locale=locale,template=t):
     e[FIELDS[0]]=locale;before=copy.deepcopy((l,b,e));calls=[];expected=[];token=object()
     prepare_bound_materials(l,b,now=n,locale=locale,required_template_id=t,pinned_pack_version=l['language_pack_versions'][locale],save_materials=expected.append)
     def save(x):calls.append(x);return token
     self.assertIs(self.prep(l,b,n,e,t,l['language_pack_versions'][locale],save),token);self.assertEqual(calls,expected);self.assertEqual((l,b,e),before)
 def test_selection_priority_and_default(self):
  l,b,n,e=self.setup()
  for field,loc in zip(FIELDS,['uk-UA','da-DK','es-ES']):e[field]=loc
  for i,field in enumerate(FIELDS):
   r=self.sel(l,b,n,e);self.assertEqual(r,{'schema_version':'SM06_LANGUAGE_SELECTION_V1','locale':e[field],'source':field});e[field]=None
  self.assertEqual(self.sel(l,b,n,e),{'schema_version':'SM06_LANGUAGE_SELECTION_V1','locale':'en-GB','source':'default'})
 def assert_code(self,code,fn):
  with self.assertRaises(impl.SM06LanguageError) as c:fn()
  self.assertEqual(c.exception.code,code);self.assertEqual(str(c.exception),code)
 def test_explicit_unavailable_no_downgrade_zero_save(self):
  l,b,n,e=self.setup();e[FIELDS[0]]='zz-ZZ';e[FIELDS[1]]='uk-UA';calls=[]
  self.assert_code('SELECTED_LOCALE_UNAVAILABLE',lambda:self.prep(l,b,n,e,save=calls.append));self.assertEqual(calls,[])
 def test_invalid_evidence_country_mixed_unknown_zero_save(self):
  l,b,n,e=self.setup()
  for bad in [None,[],{},dict(e,country='UA'),dict(e,explicit_recipient_preference=['uk-UA']),dict(e,substantive_reply_language='mixed'),dict(e,substantive_reply_language='unknown')]:
   # 'mixed'/'unknown' are valid locale-id strings syntactically: unavailable, not magic classifier flags.
   calls=[];code='SELECTED_LOCALE_UNAVAILABLE' if isinstance(bad,dict) and bad.get(FIELDS[1]) in ['mixed','unknown'] else 'INVALID_INPUT'
   self.assert_code(code,lambda:self.prep(l,b,n,bad,save=calls.append));self.assertEqual(calls,[])
 def test_registry_binding_scope_mismatch(self):
  for mode in ['version','default']:
   l,b,n,e=self.setup()
   if mode=='version':b['language_pack_versions']['uk-UA']='other-v1'
   else:b['default_locale']='ru-RU'
   self.assert_code('LANGUAGE_SCOPE_MISMATCH',lambda:self.sel(l,b,n,e))
 def test_drift_missing_blank_zero_save_passthrough(self):
  for mode in ['drift','missing','blank']:
   l,b,n,e=self.setup();e[FIELDS[0]]='uk-UA';calls=[];pin=None;t='initial'
   if mode=='drift':pin='old-version'
   elif mode=='missing':t='missing'
   else:l['packs_by_locale']['uk-UA']['templates']['initial']['body']=''
   try:prepare_bound_materials(l,b,now=n,locale='uk-UA',required_template_id=t,pinned_pack_version=pin,save_materials=lambda x:None)
   except Exception as expected:typ=type(expected);code=str(expected)
   else:self.fail('negative accepted by original dependencies')
   with self.assertRaises(typ) as c:self.prep(l,b,n,e,t,pin,calls.append)
   self.assertEqual(str(c.exception),code);self.assertEqual(calls,[])
 def test_malformed_registry_no_raw_keyerror(self):
  l,b,n,e=self.setup();del l['default_locale'];calls=[]
  with self.assertRaises(LanguageRegistryError):self.prep(l,b,n,e,save=calls.append)
  self.assertEqual(calls,[])
 def test_unapproved_fact_blank_subject_invalid_now_zero_save(self):
  for mode in ['fact','subject','now']:
   l,b,n,e=self.setup();e[FIELDS[0]]='uk-UA';calls=[]
   if mode=='fact':l['packs_by_locale']['uk-UA']['templates']['initial']['fact_ids']=['unapproved-fact']
   elif mode=='subject':l['packs_by_locale']['uk-UA']['templates']['question']['subject']=' ';t='question'
   else:n=n.replace(tzinfo=None)
   t='question' if mode=='subject' else 'initial'
   if mode=='now':typ=FirstBindingError;code='INVALID_INPUT'
   else:
    try:prepare_bound_materials(l,b,now=n,locale='uk-UA',required_template_id=t,pinned_pack_version=None,save_materials=lambda x:None)
    except Exception as expected:typ=type(expected);code=str(expected)
    else:self.fail('negative accepted by original dependencies')
   with self.assertRaises(typ) as c:self.prep(l,b,n,e,t,None,calls.append)
   self.assertEqual(str(c.exception),code);self.assertEqual(calls,[])
 def test_dependency_exception_identity(self):
  from unittest import mock
  import sales_runtime_materialization as f130
  l,b,n,e=self.setup();calls=[];error=RuleViolation('sentinel-safe-code')
  with mock.patch.object(f130,'validate_materials',side_effect=error):
   with self.assertRaises(RuleViolation) as c:self.prep(l,b,n,e,save=calls.append)
  self.assertIs(c.exception,error);self.assertEqual(calls,[])
 def test_unavailable_english_default_rejects(self):
  l,b,n,e=self.setup();b['allowed_locales'].remove('en-GB');calls=[]
  with self.assertRaises(FirstBindingError):self.prep(l,b,n,e,save=calls.append)
  self.assertEqual(calls,[])
 def test_callback_exception_identity_and_no_retry(self):
  l,b,n,e=self.setup();calls=[];error=RuntimeError('sentinel')
  def save(x):calls.append(x);raise error
  with self.assertRaises(RuntimeError) as c:self.prep(l,b,n,e,save=save)
  self.assertIs(c.exception,error);self.assertEqual(len(calls),1)
 def test_synthetic_extra_locale_no_hardcoded_enum(self):
  l,b,n,e=self.setup();locale='de-DE';p=copy.deepcopy(l['packs_by_locale']['en-GB']);p['locale']=locale;p['version']='synthetic-de-v1'
  for t in p['templates'].values():t['locale']=locale
  l['active_locales'].append(locale);l['language_pack_versions'][locale]=p['version'];l['packs_by_locale'][locale]=p;b['allowed_locales'].append(locale);b['language_pack_versions'][locale]=p['version'];e[FIELDS[0]]=locale
  self.assertEqual(self.sel(l,b,n,e)['locale'],locale)
result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Acceptance))
if not (result.wasSuccessful() and result.testsRun>0 and not result.skipped):raise SystemExit(1)
# Candidate tests supplement rather than replace frozen checks.
suite=unittest.defaultTestLoader.discover(str(P/'candidate/tests'),pattern='test*.py')
r=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if r.wasSuccessful() and r.testsRun>0 and not r.skipped else 1)
