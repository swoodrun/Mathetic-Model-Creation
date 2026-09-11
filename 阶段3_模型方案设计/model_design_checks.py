"""Artificial formula checks only. No contest optimization, fit, or backtest."""
from pathlib import Path
import json
import random

OUT=Path(__file__).resolve().parent
cfg=json.loads((OUT/'stage3_config.json').read_text(encoding='utf-8'))
checks=[]
def check(name, ok, cases):
    checks.append({'name':name,'passed':bool(ok),'cases':cases})
    assert ok,name
def near(a,b): return abs(a-b)<=1e-8*max(1,abs(a),abs(b))
def fee(g,a,p,branch):
    return p*g+(.5 if branch=='B' else -.5)*p*max(g-a,0)+1.5*p*max(a-g,0)
def step(E,a,l,r,ref,b,ec=.9,ed=.9):
    m=a+r-l; M=5000/6; R=min(10800,max(1200,ref-b))
    if m>=0:
        c=min(m,M,(10800-E)/ec); d=h=0; w=m-c
    else:
        d=min(-m,M,ed*max(E-R,0)); c=w=0; h=-m-d
    return c,d,h,w,E+ec*c-d/ed

rng=random.Random(2026)
fees=True; dominance=True
for i in range(1000):
    g=rng.uniform(0,2000); a=rng.uniform(0,2000); p=rng.uniform(.001,2)
    fees &= near(fee(g,a,p,'B'),max(1.5*p*g-.5*p*a,1.5*p*a-.5*p*g))
    fees &= near(fee(g,a,p,'A'),max(.5*p*(g+a),1.5*p*a-.5*p*g))
    if a<g: dominance &= fee(g,g,p,'B')<=fee(g,a,p,'B')
check('A_B_epigraph_equal_piecewise',fees,1000)
check('B_decrease_dominated_regular_cost',dominance,1000)
check('fee_hand_examples',fee(100,80,1,'B')==110 and fee(100,80,1,'A')==90 and fee(100,120,1,'B')==130,3)

physical=True; projection=True
for ec,ed in [(.9,.9),(.9**.5,.9**.5)]:
    for i in range(1000):
        E=rng.uniform(1200,10800); a,l,r=[rng.uniform(0,2000) for _ in range(3)]
        ref=rng.uniform(1200,10800); b=rng.choice([0,600])
        c,d,h,w,end=step(E,a,l,r,ref,b,ec,ed)
        physical &= min(c,d,h,w)>=-1e-10 and min(c,d)==0 and max(c,d)<=5000/6+1e-10
        physical &= 1200-1e-10<=end<=10800+1e-10 and near(a+r+d+h,l+c+w)
        # Generate a feasible simultaneous pair; check exact SOC/balance-preserving map.
        c=rng.uniform(0,min(5000/6,(10800-E)/ec))
        d=rng.uniform(0,min(5000/6,ed*(E+ec*c-1200)))
        delta=min(c,d/(ec*ed)); c2=c-delta; d2=d-ec*ed*delta; w2=(1-ec*ed)*delta
        projection &= near(E+ec*c-d/ed,E+ec*c2-d2/ed) and near(c-d,c2+w2-d2)
        projection &= min(c2,d2)>=-1e-8 and min(abs(c2),abs(d2))<1e-8
check('feedback_physical_constraints_two_efficiencies',physical,2000)
check('LP_cycle_projection_two_efficiencies',projection,2000)

def cvar_epigraph(values,beta):
    return min(z+sum(max(v-z,0) for v in values)/(len(values)*(1-beta)) for z in values)
def cvar_fractional_tail(values,beta):
    mass=(1-beta)*len(values); remain=mass; total=0
    for v in sorted(values,reverse=True):
        take=min(1,remain); total+=take*v; remain-=take
        if remain<=1e-12: break
    return total/mass
ok=True
for n in [1,2,3,7,20,30]:
    values=[rng.randrange(0,1000) for _ in range(n)]
    for beta in [.5,.9,.95]: ok &= near(cvar_epigraph(values,beta),cvar_fractional_tail(values,beta))
check('discrete_CVaR_fractional_tail',ok,18)
check('CVaR_ties_and_fractional_mass',near(cvar_epigraph([0,10,20],.5),50/3) and cvar_epigraph([5,5,5],.9)==5,2)
# Uniform D~U[0,100], E[(D-q)+]=(100-q)^2/200 on [0,100].
q=min(range(101),key=lambda q:q+5*(100-q)**2/200)
check('newsvendor_uniform_reference_80_percent',q==80,101)
# Once the candidate is fixed, changing only future supply leaves prefix actions unchanged.
def rollout(loads):
    E=6000; actions=[]
    for l in loads:
        row=step(E,100,l,0,4500,600); actions.append(row); E=row[-1]
    return actions
check('fixed_controller_prefix_invariance',rollout([500,600,700,800])[:2]==rollout([500,600,2000,0])[:2],2)
check('config_matches_design',cfg['risk']['main_lambda']==0 and cfg['forecast']['calendar_weekend_is_load_class'] is False and cfg['candidates']['max_intraday_including_keep']==17,1)
result={'scope':'artificial_formula_checks_only','seed':2026,'checks':checks,'passed':all(x['passed'] for x in checks),'contest_data_used':False,'optimization_run':False}
(OUT/'model_design_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'passed':result['passed'],'check_groups':len(checks),'contest_optimization':False}))
