"""Independent source-to-delivery review. Does not modify source or teammate files."""
from pathlib import Path
from datetime import datetime, timedelta
import hashlib
import json
import runpy
import sys
import numpy as np
import pandas as pd
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SRC = ROOT / '2026年数模题目和论文格式规范/C题'
TEAM = ROOT / 'C题组员支援/阶段2B/C题_阶段2B_标准数据与复现材料'
checks = []
def check(name, ok, detail=None):
    checks.append(dict(name=name, passed=bool(ok), detail=detail))
    assert ok, (name, detail)
def read_json(p): return json.loads(p.read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def close(x, y): return np.allclose(x, y, rtol=0, atol=1e-8)
def rows(name, sheet=None):
    wb=load_workbook(SRC/'附件'/name, read_only=True, data_only=True)
    ws=wb[sheet] if sheet else wb.worksheets[0]
    result=list(ws.values); wb.close(); return result

a2a=read_json(OUT/'rerun_2a/audit_evidence.json')
b2a=read_json(ROOT/'C题组员支援/阶段2A/C题_阶段2A_审计证据与复现脚本/audit_evidence.json')
for key in a2a:
    if key not in ['generated_at_local','source_root','elapsed_seconds']:
        check('audit_'+key, a2a[key]==b2a[key])
check('all_source_hashes_current', all(sha(SRC/m['file'])==m['sha256'] for m in a2a['manifest']))
manifest=read_json(TEAM/'delivery_manifest.json')
check('delivery_manifest_42_files', len(manifest)==42 and all((TEAM/m['file']).stat().st_size==m['bytes'] and sha(TEAM/m['file'])==m['sha256'] for m in manifest))
for group in ['data','eda']:
    for f in sorted((TEAM/group).glob('*.csv')):
        check('byte_equal_'+group+'/'+f.name, sha(f)==sha(OUT/'rerun_2b'/group/f.name))
summary=read_json(OUT/'rerun_2b/validation_and_summary.json')
old=read_json(TEAM/'validation_and_summary.json')
check('summary_except_elapsed', {k:v for k,v in summary.items() if k!='elapsed_seconds'}=={k:v for k,v in old.items() if k!='elapsed_seconds'})
check('preprocess_30_checks',len(summary['checks'])==30 and all(x['passed'] for x in summary['checks']))
sys.argv=['verify_stage2b.py','--input-dir',str(OUT/'rerun_2b')]
runpy.run_path(str(TEAM/'scripts/verify_stage2b.py'),run_name='__main__')
saved=read_json(OUT/'rerun_2b/independent_verification.json')
check('rerun_saved_28_checks',len(saved['checks'])==28 and saved['passed'])

# Read source cells directly; do not call the teammate ETL or its functions.
a=pd.read_csv(TEAM/'data/actual_10min.csv')
raw_load=rows('附件2.xlsx','小区负载'); raw_pv=rows('附件2.xlsx','光伏发电实际功率'); raw_price=rows('附件4.xlsx')
for raw,col in [(raw_load,'load_kw'),(raw_pv,'pv_actual_kw'),(raw_price,'price_actual_yuan_kwh')]:
    check('raw_cells_'+col,close(np.array([r[1:] for r in raw[1:]],float).ravel(),a[col]))
expected_end=[r[0]+timedelta(minutes=10*k) for r in raw_load[1:] for k in range(1,145)]
check('all_timestamp_endpoints',pd.to_datetime(a.interval_end).tolist()==expected_end)
check('observations_available_at_end',(a.observation_available_at==a.interval_end).all())
check('interval_start_and_operating_date',(pd.to_datetime(a.interval_start)==pd.to_datetime(a.interval_end)-pd.Timedelta(minutes=10)).all() and (pd.to_datetime(a.date)==pd.to_datetime(a.interval_start).dt.normalize()).all())
check('energy_net_sign_retained', close(a.load_kwh,a.load_kw/6) and close(a.pv_actual_kwh,a.pv_actual_kw/6) and close(a.net_load_kwh,(a.load_kw-a.pv_actual_kw)/6))
q=pd.read_csv(TEAM/'data/q1_inputs.csv'); raw_q=rows('附件1.xlsx')
check('q1_raw_cells',close(q[['price_yuan_kwh','load_kw','pv_forecast_kw']],np.array([r[1:] for r in raw_q[1:]],float)))
tariff=pd.read_csv(TEAM/'data/fixed_tariff_q2_q3.csv')
check('fixed_tariff_only_given_price',tariff.columns.tolist()==['slot','start_minute','end_minute','price_yuan_kwh'] and close(tariff.price_yuan_kwh,q.price_yuan_kwh))

f=pd.read_csv(TEAM/'data/pv_forecast_10min.csv'); h=pd.read_csv(TEAM/'data/pv_forecast_hourly.csv')
raw_f=rows('附件3.xlsx'); obs=dict(zip(expected_end,a.pv_actual_kw))
expected_linear=[]; expected_step=[]; expected_issue=[]; expected_target=[]; expected_hourly=[]; assumptions=[]
day=None
for r in raw_f[1:]:
    if r[0] is not None and str(r[0]).strip(): day=pd.Timestamp(r[0]).to_pydatetime()
    release=r[1].hour if hasattr(r[1],'hour') else int(str(r[1]).split(':')[0])
    issue=day+timedelta(hours=release)
    if issue not in obs: assumptions.append(issue)
    points=[obs.get(issue,0.0)]+[float(v) for v in r[2:]]
    expected_hourly.extend(points[1:])
    for k in range(1,145):
        upper=(k+5)//6; numerator=k-6*(upper-1)
        # Weighted endpoint formula independently implemented, without np.interp.
        expected_linear.append(((6-numerator)*points[upper-1]+numerator*points[upper])/6)
        expected_step.append(points[upper]); expected_issue.append(issue); expected_target.append(issue+timedelta(minutes=k*10))
check('every_hourly_forecast_raw_value',close(h.pv_forecast_kw,expected_hourly))
check('every_linear_interpolation',close(f.pv_linear_kw,expected_linear))
check('every_step_interpolation',close(f.pv_step_kw,expected_step))
check('forecast_issue_target_alignment',pd.to_datetime(f.issue_datetime).tolist()==expected_issue and pd.to_datetime(f.interval_end).tolist()==expected_target)
check('forecast_availability_exact',(f.available_at==f.issue_datetime).all() and (f.anchor_available_at==f.issue_datetime).all())
check('only_initial_anchor_assumption',assumptions==[datetime(2025,1,1)])
within=[t<=i.replace(hour=0)+timedelta(days=1) for i,t in zip(expected_issue,expected_target)]
check('within_issue_day_all_rows',np.array_equal(f.within_issue_day,within))
e=pd.read_csv(TEAM/'eda/forecast_errors_evaluation_only.csv')
truth=np.array([obs.get(t,np.nan) for t in expected_target])
check('every_evaluation_truth_matches_source',np.allclose(e.pv_actual_kw,truth,rtol=0,atol=1e-8,equal_nan=True))
check('all_errors_sign_and_missing',np.allclose(e.error_linear_kw,np.array(expected_linear)-truth,rtol=0,atol=1e-8,equal_nan=True) and np.allclose(e.error_step_kw,np.array(expected_step)-truth,rtol=0,atol=1e-8,equal_nan=True))
check('out_of_range_not_zero_filled',int(np.isnan(truth).sum())==216)
check('error_availability_exact',(e.error_available_at==e.interval_end).all())
check('2026_midnight_four_valid_versions',sum(t==datetime(2026,1,1) and np.isfinite(v) for t,v in zip(expected_target,truth))==4)
# Recompute every reported interpolation metric, including evaluation windows and strata.
scores=pd.read_csv(TEAM/'eda/interpolation_metrics.csv'); issue=pd.DatetimeIndex(expected_issue)
lead=np.tile(np.arange(1,145),1460); valid=np.isfinite(truth)
for s in scores.itertuples():
    mask=valid & (issue>=pd.Timestamp('2025-02-01' if s.period=='feb_dec' else '2025-01-01')) & (issue.hour==s.release_hour)
    if s.domain=='remaining_issue_day': mask &= np.array(within)
    if s.region=='actual_positive': mask &= truth>0
    if s.region=='first_hour': mask &= lead<=6
    pred=np.array(expected_linear if s.method=='linear' else expected_step)
    err=pred[mask]-truth[mask]
    assert len(err)==s.n and close([abs(err).mean(),np.sqrt((err**2).mean()),err.mean()],[s.mae_kw,s.rmse_kw,s.bias_pred_minus_actual_kw]), s
check('all_interpolation_metric_rows',True,len(scores))
daily_load=np.array([r[1:] for r in raw_load[1:]],float).sum(axis=1)/6
january=[(r[0].weekday(),v) for r,v in zip(raw_load[1:32],daily_load[:31])]
janmeans={d:float(np.mean([v for w,v in january if w==d])) for d in range(7)}
check('january_supports_fri_sat_low_pattern',max(janmeans[4],janmeans[5])<min(v for d,v in janmeans.items() if d not in (4,5)),janmeans)
check('source_files_still_unchanged',all(sha(SRC/m['file'])==m['sha256'] for m in a2a['manifest']))
result=dict(passed=all(c['passed'] for c in checks),check_count=len(checks),checks=checks,
            statement='Source-to-delivery deterministic verification; no optimization or strategy backtest performed.')
(OUT/'independent_review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'passed':result['passed'],'check_count':len(checks),'metric_rows':len(scores)},ensure_ascii=False))
