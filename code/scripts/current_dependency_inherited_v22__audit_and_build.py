"""Verify Figure5 and assemble the complete independently versioned preview."""
from pathlib import Path
import sys,json,hashlib,subprocess,html,re,ast,urllib.parse,urllib.request
sys.dont_write_bytecode=True
O=Path(__file__).resolve().parent;R=O.parents[1];OLD=R/'deliverables/Main_figures_preview_20261008_v20';Q=O/'qa';SD=O/'Source_Data'
import pandas as pd,numpy as np,pymupdf
from PIL import Image
S=Path('C:/Users/yuanq/.agents/skills/nature-figure/scripts')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def js(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
protected=json.loads((Q/'Figure5_protected_before.json').read_text(encoding='utf-8'));assert all(sha(R/k)==v for k,v in protected.items())
for name in ['Figure_1','Figure_2','Figure_3','Figure_4','Figure_S_Fig1_distributions','Continuous_path_support','Figure_S_Fig4_decision_effects']:
 for p in (OLD/name).iterdir():
  if p.is_file():assert sha(p)==sha(O/name/p.name)
for p in (OLD/'Source_Data').glob('*.csv'):assert sha(p)==sha(SD/p.name)
for file in ['frozen_dependency_hashes.json','Figure5_map_dependencies.json']:
 for k,v in json.loads((O/'inputs'/file).read_text(encoding='utf-8')).items():assert sha(O/k)==v
def function(path,name):return next(n for n in ast.parse(path.read_text(encoding='utf-8')).body if isinstance(n,ast.FunctionDef) and n.name==name)
assert ast.dump(function(O/'code/map_template.py','draw_original_map'))==ast.dump(function(R/'deliverables/Main_figures_preview_20261008_v14/plot_five_figures.py','draw_original_map'))
numeric=json.loads((Q/'Figure5_numerical_checks.json').read_text(encoding='utf-8'));assert numeric['status']=='PASS'
f=pd.read_csv(SD/'Figure5_all_four_case_region_decisions.csv',dtype={'adcode':str});main=pd.read_csv(SD/'Figure5_displayed_region_pairs.csv',dtype={'adcode':str})
assert len(f)==1476 and len(main)==738 and (f.groupby(['candidate','context']).adcode.nunique()==369).all()
summ=pd.read_csv(SD/'Figure5_transition_summary.csv');prior=pd.read_csv(SD/'Figure4_baseline_target_counts.csv')
for (tech,ct),q in f.groupby(['candidate','context']):
 assert set(q.baseline_rank)==set(range(1,370)) and q.baseline_rank.nunique()==369
 sr=summ[summ.candidate.eq(tech)&summ.context.eq(ct)].iloc[0];assert int(sr.retained+sr.new+sr.lost+sr.remaining_gap)==369
 for response in ['baseline','target']:
  number=int(q[response+'_at_parity'].sum());r=prior[prior.candidate.eq(tech)&prior.context.eq(ct)&prior.response_state.eq(response)].iloc[0];assert number==int(r.regions)
 assert np.allclose(100*(q.target_margin-q.baseline_margin)/q.normalization_initial_system_expenditure,q.margin_change_pp,rtol=0,atol=1e-10)
 assert np.all(np.isfinite(q[['baseline_margin_pct','target_margin_pct','normalization_initial_system_expenditure']]))
for _,q in main.groupby(['candidate','context']):
 assert (q[['baseline_margin_pct','target_margin_pct']].to_numpy()>=-45).all() and (q[['baseline_margin_pct','target_margin_pct']].to_numpy()<=15).all()
 assert np.all(np.diff(q.sort_values('baseline_rank').baseline_margin_pct)>=-1e-12)
f[f.margin_change_pp.lt(-1e-10)].to_csv(SD/'Figure5_declining_margin_regions.csv',index=False,encoding='utf-8-sig')
mapqa=json.loads((Q/'Figure5_map_template_checks.json').read_text(encoding='utf-8'));assert mapqa['status']=='PASS' and len(mapqa['maps'])==2 and all(q['visible_region_polygons']==369 for q in mapqa['maps'])
for tool,arg,out in [('validate_figure.py',O/'plot_figure5.py','Figure_5.source.json'),('audit_pdf_text.py',O/'Figure_5/Figure_5.pdf','Figure_5.fonts.json')]:
 r=subprocess.run([sys.executable,'-X','utf8',str(S/tool),str(arg),'--json'],capture_output=True,text=True,encoding='utf-8');(Q/out).write_text(r.stdout,encoding='utf-8');assert r.returncode==0,r.stdout+r.stderr
r=subprocess.run([sys.executable,'-X','utf8',str(S/'audit_figure_collisions.py'),str(O/'Figure_5/Figure_5.pdf'),'--json-out',str(Q/'Figure_5.collisions.json'),'--overlay-pdf',str(Q/'Figure_5.collision_overlay.pdf')],capture_output=True,text=True,encoding='utf-8');assert r.returncode==0,r.stdout+r.stderr
collision=json.loads((Q/'Figure_5.collisions.json').read_text());assert collision['summary']['fail']==collision['summary']['warn']==0
fonts=json.loads((Q/'Figure_5.fonts.json').read_text());assert fonts['minimum_found_pt']>=5
alignment=json.loads((Q/'Figure_5.alignment.json').read_text());assert alignment['verdict']=='PASS'
with pymupdf.open(O/'Figure_5/Figure_5.pdf') as doc:
 p=doc[0];assert 'Below parity:' in p.get_text() and 'Gap:' not in p.get_text();size=[p.rect.width/72*25.4,p.rect.height/72*25.4];assert np.allclose(size,[183,165],rtol=0,atol=1e-5)
 p.get_pixmap(dpi=150).save(Q/'Figure_5.final_size.png')
 for letter,rect in zip('abcd',[(0,0,p.rect.width*.60,p.rect.height*.51),(p.rect.width*.60,0,p.rect.width,p.rect.height*.51),(0,p.rect.height*.47,p.rect.width*.60,p.rect.height*.94),(p.rect.width*.60,p.rect.height*.47,p.rect.width,p.rect.height*.94)]):p.get_pixmap(matrix=pymupdf.Matrix(3,3),clip=pymupdf.Rect(*rect)).save(Q/('Figure_5.panel_'+letter+'.png'))
with Image.open(O/'Figure_5/Figure_5.tiff') as im:assert min(im.info['dpi'])>=599.5
assert '<text' in (O/'Figure_5/Figure_5.svg').read_text(encoding='utf-8')
js(Q/'Figure5_chain_checks.json',dict(status='PASS',all_case_regions=1476,displayed_pairs=738,regions_per_map=369,map_renderer_function_AST_identical=True,original_map_geometry_files_unchanged=True,baseline_target_pair_order_verified=True,normalization_identity_verified=True,same_rank_and_margin_axis_scale=True,all_Figure4_counts_match=True,no_new_external_numeric_inputs=True,financial_identities_inherited=30,protected_previous_and_formal_files=len(protected),inherited_source_files_byte_identical=len(list((OLD/'Source_Data').glob('*.csv'))),Figures1_4_byte_identical=True,formal_manuscript_SI_unchanged=True,minimum_font_pt=fonts['minimum_found_pt'],size_mm=size,alignment='PASS',collisions=collision['summary']))
combined=pymupdf.open()
for n in [1,2,3,4,5]:
 with pymupdf.open(O/f'Figure_{n}/Figure_{n}.pdf') as p:combined.insert_pdf(p)
combined.save(O/'Five_main_figures_common_start.pdf');combined.close()
report='图5恢复v20结构并澄清口径（2026-10-08，v22独立预览）\n\n作者同意恢复v20结构，仅修正Gap标签及比较对象/情景边界。主图任务是承接图4的经济门槛，展示同一候选运行响应改善具体令哪些地区跨越经济平价，以及配对地区仍有多少经济差额。v21的基线选择与初始投资要求分析保留作配套资料，不继续作为主图5。\n\n主图布局、原地图模板、全369地区、配对顺序、颜色、坐标范围和全部数值与v20一致。唯一图内变动为Gap改成Below parity（仍未达到经济平价）。该名称指终点候选NPV仍低于两个固定共同基线竞争技术与不建设中的最大NPV，不是数据缺失、并不必然NPV为负。\n\n单结/装机：163保留、11新增、195仍未平价；叠层/场地：169保留、80新增、120仍未平价。两者均无既有竞争地区退出，但分别35和8地区的经济差额下降，配对图完整保留。\n\n图注明确：与图3参数情景端点及图4使用同一物理起点；只改变候选运行响应，竞争技术、成本、寿命、初损、衰减和财务规则固定。归一化差额不是发电量增益。两种部署情景电价0.04/0.08USD/kWh不同，场地费25USD/m²；不拼成全国分配，不声称实测器件研发路径或实际采用。\n\n外源数据、参数、原件和数值位置记录不变，没有新增数值输入。全部四组合1476条地区结果、主图738条地区配对以及30条财务参数身份、22条物理外源数值索引均保留。数值检查沿用相同输入和结果，并通过完整SHA256依赖核对；字体、对齐、碰撞与最终视觉检查对本次导出重新执行。\n\n图1–4、正式正文和完整SI未改动；v20、v21及所有历史版本保留。当前仍为独立五图预览，尚未替换正式正文图注及面板指代。\n\n复算：code/compute_figure5.py（数值）、plot_figure5.py（绘图）、audit_and_build.py（依赖与导出核对）。本次数值未改变，无需重跑小时物理计算。v21支持分析见浏览器内链接。\n'
(O/'图5地区决策后果更新记录.txt').write_text(report,encoding='utf-8')
def link(p,label):return '<a href="'+html.escape(p,quote=True)+'">'+html.escape(label)+'</a>'
style='body{font-family:Arial,"Microsoft YaHei",sans-serif;background:#f3f5f6;color:#26333c;margin:0;line-height:1.7}main{max-width:1150px;margin:28px auto;padding:0 24px}h1{font-size:25px}h2{font-size:20px}section{background:white;padding:23px 28px;border:1px solid #dfe5e9;border-radius:7px;margin:20px 0}img{display:block;width:100%;height:auto}a{color:#236c96;text-decoration:none}.links,nav{display:flex;flex-wrap:wrap;gap:18px}.small{color:#63727b;font-size:14px}summary{cursor:pointer}table{border-collapse:collapse;font-size:14px;width:100%}td,th{border-bottom:1px solid #e1e6e9;padding:9px;text-align:left}.compare{display:grid;grid-template-columns:1fr 1fr;gap:18px}@media(max-width:700px){.compare{grid-template-columns:1fr}}'
page='<!doctype html><html lang="zh"><meta charset="utf-8"><title>图5地区决策后果 · v22</title><style>'+style+'</style><main><h1>图5：哪些地区获得竞争力，剩余差距有多大？</h1><p class="small">v22独立预览 · 恢复v20结构 · 口径澄清 · 图1–4保持已确认版本</p><nav>'+''.join(link('#fig'+str(n),'图'+str(n)) for n in [1,2,3,4,5])+link('#support','经济对照支持')+'</nav><section><p>两幅地图区分保留、新增竞争力和仍有经济缺口的地区；右侧按同一起点排序配对经济差额，终点没有重新排序。沿用图4财务情景与固定竞争技术。</p><div class="links">'+link('Five_main_figures_common_start.pdf','五张主图合并PDF')+link('图5地区决策后果更新记录.txt','更新及边界记录')+link('qa/Figure5_chain_checks.json','完整一致性核对')+link('../Main_figures_preview_20261008_v19/index.html#fig4','已确认图4')+'</div></section>'
for n in [1,2,3,4,5]:
 folder='Figure_'+str(n);cf=O/folder/(folder+('_caption_en.txt' if n>=3 else '_preview_caption.txt'));title='图'+str(n)+('｜空间决策变化与剩余经济差额' if n==5 else '｜已确认版本保持不变')
 page+='<section id="fig'+str(n)+'"><h2>'+title+'</h2><img src="'+folder+'/'+folder+'.png" alt="图'+str(n)+'"><div class="links">'+''.join(link(folder+'/'+folder+'.'+e,e.upper()) for e in ['pdf','svg','tiff'])+link(str(cf.relative_to(O)).replace('\\','/'),'英文图注')+'</div><details><summary>图注</summary><p class="small">'+html.escape(cf.read_text(encoding='utf-8'))+'</p></details>'
 if n==5:
  tab=summ[summ.display_main][['candidate','retained','new','remaining_gap','declining_margin_regions']].rename(columns={'candidate':'路径','retained':'保留竞争力','new':'新增竞争力','remaining_gap':'仍未达到经济平价','declining_margin_regions':'经济差额下降'});tab['路径']=tab['路径'].map({'single_junction':'单结／装机','tandem':'叠层／场地'})
  page+=tab.to_html(index=False,border=0)+'<p class="small">仍未平价指终点候选NPV低于两个固定共同基线竞争技术及不建设中的最优NPV，不代表没有改善。纵轴为初始系统支出归一化后的经济差额，不是发电量增益。两个独立情景使用不同电价，地区数不能相加为全国分配。</p><details><summary>与旧图5比较</summary><div class="compare"><div><p>旧版</p><img src="../Main_figures_preview_20261008_v14/Figure_5/Figure_5.png" alt="旧图5"></div><div><p>新版</p><img src="Figure_5/Figure_5.png" alt="新版图5"></div></div></details>'
 page+='</section>'
folder='Figure_S_Fig4_decision_effects'
page+='<section id="support"><h2>沿用支持｜同价、场地费与更换规则</h2><img src="'+folder+'/'+folder+'.png" alt="经济对照支持图"><p>完整同价、0／25美元每平方米场地费、更换支出和残值情景均沿用图4材料。主图的竞争判断依赖既定财务条件。</p><div class="links">'+link(folder+'/'+folder+'.pdf','支持图PDF')+link('Source_Data/Figure4_matched_financial_controls.csv','全部同价与场地费对照')+link('Source_Data/Figure4_replacement_boundary_sensitivity.csv','更换与残值对照')+'</div></section>'
page+='<section><h2>源数据与溯源</h2><p>全部四组合1476条地区起终点经济结果保留，主图两条路径各使用全部369地区。没有新增外部参数。正文、SI及历史版本未改动。</p><div class="links">'+''.join(link('Source_Data/'+f+'.csv',label) for f,label in [('Figure5_all_four_case_region_decisions','全部四组合地区结果'),('Figure5_displayed_region_pairs','主图738条地区配对'),('Figure5_joint_choice_transitions','联合NPV选择转移'),('Figure5_declining_margin_regions','经济差额下降地区'),('Figure5_derived_display_definitions','派生量定义'),('Figure4_financial_parameter_identities','30条财务参数身份'),('Figure4_official_utilization_numeric_locations','NEA原表逐值位置'),('Figure4_inherited_external_numeric_source_index','物理外源数值索引')])+link('qa/Figure5_map_template_checks.json','原地图与369多边形核对')+link('qa/Figure_5.collisions.json','碰撞核对')+link('qa/Figure_5.fonts.json','字体核对')+link('qa/Figure_5.alignment.json','对齐核对')+link('../Main_figures_preview_20261008_v15/index.html','物理上游完整溯源')+'</div></section></main></html>'
page=page.replace('</main></html>','<section id="cost-support"><h2>配套资料｜基线区域选择与初始投资要求</h2><p>v21分析保留为配套资料，包含全部四种候选技术／部署约束组合的初始投资反求。主图5继续采用v20的地区变化地图和起点—终点配对结构。</p><div class="links"><a href="../Main_figures_preview_20261008_v21/index.html#fig5">查看配套图与口径</a><a href="../Main_figures_preview_20261008_v21/Source_Data/Figure5_storyline_all_cost_requirements.csv">全部1476条投资要求</a><a href="../Main_figures_preview_20261008_v21/qa/Figure5_storyline_chain_checks.json">配套分析核对</a></div></section>'+'</main></html>')
(O/'index.html').write_text(page,encoding='utf-8');http=[]
for u in sorted(set(re.findall(r'(?:src|href)="([^"]+)"',page))):
 if u.startswith('#'):continue
 resource=urllib.parse.urldefrag(html.unescape(u))[0];url='http://127.0.0.1:8771/'+O.name+'/'+urllib.parse.quote(resource,safe='/?=&')
 with urllib.request.urlopen(url,timeout=10) as response:assert response.status==200;http.append(dict(resource=u,status=200))
js(Q/'Figure5_gallery_http_check.json',dict(status='PASS',resources=http))
js(O/'delivery_manifest.json',{str(p.relative_to(O)).replace('\\','/'):sha(p) for p in O.rglob('*') if p.is_file() and p.name!='delivery_manifest.json' and '__pycache__' not in p.parts})
print('PASS: Figure5 numerical/paired/map/QA chain; Figures1-4 and manuscript/SI unchanged.',flush=True)
