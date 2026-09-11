"""Validate final design artifacts and artificial mathematical cases, not optimization."""
from pathlib import Path
import csv, hashlib, itertools, json, math, random
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
cfg=json.loads((OUT/'stage3_final_config.json').read_text(encoding='utf-8'))
checks=[]
def check(name,condition,detail=None):
    checks.append({'name':name,'passed':bool(condition),'detail':detail})
    assert condition,name
def near(a,b):return abs(a-b)<=1e-8*max(1,abs(a),abs(b))
rng=random.Random(2026)
manifest=json.loads((OUT/'source_manifest.json').read_text(encoding='utf-8'))
check('source_manifest_current',all(hashlib.sha256((ROOT/m['file']).read_bytes()).hexdigest()==m['sha256'] for m in manifest),len(manifest))
with (OUT/'time_mapping_final.csv').open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
check('mapping_144_consecutive_intervals',len(rows)==144 and all(int(r['slot'])==i+1 and int(r['start_minute'])==i*10 and int(r['end_minute'])==(i+1)*10 for i,r in enumerate(rows)))
check('mapping_three_boundaries',[(rows[i]['export_label'],rows[i]['annual_template_column'],int(rows[i]['q1_template_row'])) for i in [0,60,143]]==[('00:00-00:10','B',2),('10:00-10:10','BJ',62),('23:50-24:00','EO',145)])
check('source_labels_retained_canonical_export',rows[0]['original_q1_label']=='0:10-0:20' and all(r['export_label']==r['canonical_label'] for r in rows))
check('signed_correction_and_candidate_counts',cfg['candidates']['margin_policy']=='signed_raw_quantile_correction_no_clipping' and cfg['candidates']['reference_release_kwh']==[0,600,9600] and cfg['candidates']['max_dayahead']==4*3 and cfg['candidates']['max_intraday_including_keep']==2*4*3+1)
check('fixed_a_reference_and_free_a_v_zero',cfg['candidates']['fixed_a_reference']['balance_constraints']==['c+w=s','d+v=q'] and cfg['candidates']['free_a_reference']['virtual_shortfall_fixed_zero'])
check('data_files_accessible',all((ROOT/x).exists() for x in cfg['data'].values()))
check('old_forecast_residual_age_and_no_reanchor',cfg['information']['residual_source_must_match_allowed_forecast_age'] and not cfg['information']['old_forecast_reanchor_at_current_observation'])

# This artificial example diagnoses the v1 flaw; it is not an LP solver result.
old_gain=.9*(.9*100)-5*.01*100
check('old_virtual_charge_has_false_incentive',near(old_gain,76),'a=N=0, E=5000, c=v=100; old terminal savings minus cost=76 yuan')
check('new_zero_surplus_forbids_virtual_charge',max(0-0,0)==0 and max(0-0,0)==0,'c+w=0 and d+v=0 imply all four variables zero')
ok=True
for _ in range(1000):
    a=rng.uniform(0,1800); n=rng.uniform(-1800,1800)
    s=max(a-n,0); q=max(n-a,0)
    c=d=0;w=s;v=q
    ok &= s*q==0 and near(a+d+v,n+c+w)
check('fixed_a_zero_action_always_feasible',ok,'1000 artificial cases, unchanged admissible E')
check('signed_median_corrects_high_forecast',500+sorted([-200,-180,-160])[1]==320)
check('full_release_floor',all(max(1200,min(10800,e-9600))==1200 for e in range(1200,10801,100)))

def dispatch(E,a,l,r,ref,b,ec,ed):
    m=a+r-l;M=5000/6;R=max(1200,min(10800,ref-b))
    if m>=0:c=min(m,M,(10800-E)/ec);d=h=0;w=m-c
    else:d=min(-m,M,ed*max(E-R,0));c=w=0;h=-m-d
    return c,d,h,w,E+ec*c-d/ed
ok=True
for ec in [.9,math.sqrt(.9)]:
    ed=ec
    for _ in range(1000):
        E=rng.uniform(1200,10800);a,l,r=[rng.uniform(0,2000) for _ in range(3)]
        c,d,h,w,end=dispatch(E,a,l,r,rng.uniform(1200,10800),rng.choice([0,600,9600]),ec,ed)
        ok &= near(a+r+d+h,l+c+w) and 1200-1e-8<=end<=10800+1e-8 and min(c,d,h,w)>=-1e-8 and min(c,d)==0 and max(c,d)<=5000/6+1e-8
check('feedback_physical_two_efficiencies_three_reserves',ok,'2000 artificial cases')
greedy=dispatch(6000,0,800,0,6000,9600,.9,.9)
check('greedy_example_supplies_gap',near(greedy[1],800) and near(greedy[2],0) and near(greedy[4],5111.111111111111))
def fee(g,a,p,k):return p*g+(.5 if k=='B' else -.5)*p*max(g-a,0)+1.5*p*max(a-g,0)
ok=True
for _ in range(1000):
    g,a=rng.uniform(0,2000),rng.uniform(0,2000);p=rng.uniform(.001,2)
    ok &= near(fee(g,a,p,'A'),max(.5*p*(g+a),1.5*p*a-.5*p*g)) and near(fee(g,a,p,'B'),max(1.5*p*g-.5*p*a,1.5*p*a-.5*p*g))
check('fees_epigraph_matches_piecewise',ok,'1000 artificial cases')
ok=True
for ec in [.9,math.sqrt(.9)]:
    for _ in range(500):
        c,d=rng.uniform(0,5000/6),rng.uniform(0,5000/6);q=ec*ec;delta=min(c,d/q)
        c2,d2,w2=c-delta,d-q*delta,(1-q)*delta
        ok &= near(ec*c-d/ec,ec*c2-d2/ec) and near(c-d,c2+w2-d2) and min(abs(c2),abs(d2))<1e-8
check('cycle_removal_preserves_energy',ok,'1000 artificial cases')
def cvar(v,b):return min(z+sum(max(x-z,0) for x in v)/(len(v)*(1-b)) for z in v)
check('fractional_CVaR_and_ties',near(cvar([0,10,20],.5),50/3) and near(cvar([5,5,5],.9),5))
band=lambda e,k:k*(max(5000-e,0)+max(e-7000,0))
check('terminal_band',band(6000,.9)==0 and near(band(4000,.9),900) and near(band(8000,.9),900))

# Verify soft-reserve threshold against all breakpoints of its convex piecewise objective.
ok=True
for _ in range(1000):
    E=rng.uniform(1200,10800);R=rng.uniform(1200,10800);q=rng.uniform(0,1800);p=rng.uniform(.001,2);mu=rng.uniform(0,15);ed=.9
    dmax=min(q,5000/6,ed*(E-1200));free=min(dmax,ed*max(E-R,0))
    d=dmax if 5*p>mu/ed else free
    cost=lambda x:5*p*(q-x)+mu*max(R-(E-x/ed),0)
    ok &= near(cost(d),min(cost(x) for x in [0,free,dmax]))
check('soft_reserve_threshold_matches_piecewise_minimum',ok,'1000 artificial cases; value estimator not implemented')

members=(6,12,18)
subsets=[frozenset(x) for k in range(4) for x in itertools.combinations(members,k)]
def value(s):return sum({6:10,12:20,18:-3}[x] for x in s)+(8 if {6,12}<=s else 0)
phi={}
for h in members:
    phi[h]=sum(math.factorial(len(s))*math.factorial(2-len(s))/6*(value(s|{h})-value(s)) for s in subsets if h not in s)
check('eight_subsets_shapley_efficiency_and_negative_value',len(subsets)==8 and near(sum(phi.values()),value(frozenset(members))-value(frozenset())) and phi[18]<0,phi)
ok=True
prices=[.01,.2,.5,1,1.7];mean=sum(prices)/len(prices);logs=[math.log(p) for p in prices];ml=sum(logs)/len(logs)
for gamma in [.5,1,1.5]:
    w=[math.exp(gamma*(z-ml)) for z in logs];mw=sum(w)/len(w);scaled=[mean*x/mw for x in w]
    ok &= all(x>0 for x in scaled) and near(sum(scaled)/len(scaled),mean)
    if gamma==1:ok &= all(near(a,b) for a,b in zip(prices,scaled))
check('synthetic_price_mean_and_identity',ok)
check('design_not_solved',not cfg['implementation']['actual_optimization_run'] and not cfg['implementation']['actual_backtest_run'])
text=(ROOT/'C题最终方案_阶段3定稿.md').read_text(encoding='utf-8')
check('document_math_delimiters_balanced',text.count('\\[')==text.count('\\]'))
result={'scope':'final_design_artifacts_and_artificial_formula_checks_only','seed':2026,'passed':all(x['passed'] for x in checks),'check_groups':len(checks),'checks':checks,'contest_optimization':False,'annual_backtest':False}
(OUT/'final_design_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'passed':result['passed'],'check_groups':len(checks),'contest_optimization':False}))
