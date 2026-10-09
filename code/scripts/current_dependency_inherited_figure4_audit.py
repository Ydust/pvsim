"""Verify the complete numerical/figure chain and assemble the independent preview."""
from pathlib import Path
import sys,json,hashlib,subprocess,html,re,urllib.request,urllib.parse
sys.dont_write_bytecode=True
O=Path(__file__).resolve().parent;R=O.parents[1];OLD=R/'deliverables/Main_figures_preview_20261008_v18'
import pandas as pd,numpy as np,pymupdf
from PIL import Image
S=Path('C:/Users/yuanq/.agents/skills/nature-figure/scripts');Q=O/'qa';SD=O/'Source_Data'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def js(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def read(name):return pd.read_csv(SD/(name+'.csv'),dtype={'adcode':str})
protected=json.loads((Q/'protected_before.json').read_text(encoding='utf-8'))
assert all(sha(R/k)==v for k,v in protected.items())
for name in ['Figure_1','Figure_2','Figure_3','Figure_S_Fig1_distributions','Continuous_path_support']:
 for p in (OLD/name).iterdir():
  if p.is_file():assert sha(p)==sha(O/name/p.name)
for p in (OLD/'Source_Data').glob('*.csv'):assert sha(p)==sha(SD/p.name)
for k,v in json.loads((O/'inputs/frozen_dependency_hashes.json').read_text(encoding='utf-8')).items():assert sha(O/k)==v
f=read('Figure4_common_start_frontiers');g=read('Figure4_national_coverage_grid');th=read('Figure4_coverage_thresholds');counts=read('Figure4_baseline_target_counts')
assert len(f)==4*2*41*369 and len(g)==4*2*41*201 and len(th)==4*2*41*2
assert (f.groupby(['candidate','context','response_state','lifetime_years']).adcode.nunique()==369).all()
groups=['candidate','context','response_state','lifetime_years'];maxcov=0.;maxthreshold=0.
for key,z in f.groupby(groups):
 b=np.sort(z.parity_initial_cost_usd_wp.to_numpy())
 q=g
 for col,val in zip(groups,key):q=q[q[col].eq(val)]
 direct=(b[:,None]>=q.initial_system_cost_usd_wp.to_numpy()[None,:]-1e-12).sum(axis=0)/369*100
 maxcov=max(maxcov,float(np.max(np.abs(direct-q.coverage_pct.to_numpy()))))
 q=th
 for col,val in zip(groups,key):q=q[q[col].eq(val)]
 for row in q.itertuples():maxthreshold=max(maxthreshold,abs(row.initial_system_cost_usd_wp-b[369-int(row.required_regions)]))
assert maxcov<1e-12 and maxthreshold<1e-12
ident=read('Figure4_financial_parameter_identities')
for row in ident.itertuples():
 file=row.numeric_locator.split(':')[0];assert sha(O/file)==row.code_sha256
external=read('Figure4_inherited_external_numeric_source_index')
assert all(sha(O/row.source_file)==row.source_sha256 for row in external.itertuples())
num=json.loads((Q/'Figure4_numerical_checks.json').read_text());prov=json.loads((Q/'Figure4_provenance_checks.json').read_text());assert num['status']==prov['status']=='PASS'
render={}
for folder,source in [('Figure_4','plot_figure4.py'),('Figure_S_Fig4_decision_effects','plot_figure4_support.py')]:
 for tool,arg,out in [('validate_figure.py',O/source,folder+'.source.json'),('audit_pdf_text.py',O/folder/(folder+'.pdf'),folder+'.fonts.json')]:
  result=subprocess.run([sys.executable,str(S/tool),str(arg),'--json'],capture_output=True,text=True,encoding='utf-8')
  (Q/out).write_text(result.stdout,encoding='utf-8');assert result.returncode==0,result.stdout+result.stderr
 result=subprocess.run([sys.executable,str(S/'audit_figure_collisions.py'),str(O/folder/(folder+'.pdf')),'--json-out',str(Q/(folder+'.collisions.json')),'--overlay-pdf',str(Q/(folder+'.collision_overlay.pdf'))],capture_output=True,text=True,encoding='utf-8')
 assert result.returncode==0,result.stdout+result.stderr
 collision=json.loads((Q/(folder+'.collisions.json')).read_text());assert collision['summary']['fail']==0 and collision['summary']['warn']==0
 alignment=json.loads((Q/(folder+'.alignment.json')).read_text());assert alignment['verdict']=='PASS'
 fonts=json.loads((Q/(folder+'.fonts.json')).read_text());assert fonts['minimum_found_pt']>=5
 with pymupdf.open(O/folder/(folder+'.pdf')) as doc:
  p=doc[0];size=[p.rect.width/72*25.4,p.rect.height/72*25.4];assert abs(size[0]-183)<1e-5
  p.get_pixmap(dpi=150).save(Q/(folder+'.final_size.png'))
  for letter,rect in zip('abcd',[(0,0,p.rect.width/2,p.rect.height*.50),(p.rect.width*.50,0,p.rect.width,p.rect.height*.50),(0,p.rect.height*.46,p.rect.width/2,p.rect.height*.91),(p.rect.width*.50,p.rect.height*.46,p.rect.width,p.rect.height*.91)]):
   p.get_pixmap(matrix=pymupdf.Matrix(3,3),clip=pymupdf.Rect(*rect)).save(Q/(folder+'.panel_'+letter+'.png'))
 with Image.open(O/folder/(folder+'.tiff')) as im:assert min(im.info['dpi'])>=599.5
 assert '<text' in (O/folder/(folder+'.svg')).read_text(encoding='utf-8')
 render[folder]=dict(size_mm=size,minimum_font_pt=fonts['minimum_found_pt'],alignment='PASS',collision_summary=collision['summary'])
summary=[]
for (tech,ct),z in counts.groupby(['candidate','context'],sort=False):
 z=z.set_index('response_state');L=float(z.loc['baseline','lifetime_years']);q=th[th.candidate.eq(tech)&th.context.eq(ct)&th.lifetime_years.eq(L)].set_index(['response_state','minimum_coverage_pct'])
 summary.append(dict(candidate=tech,context=ct,baseline_regions=int(z.loc['baseline','regions']),target_regions=int(z.loc['target','regions']),life=L,baseline_cost50=float(q.loc[('baseline',50),'initial_system_cost_usd_wp']),target_cost50=float(q.loc[('target',50),'initial_system_cost_usd_wp']),baseline_cost100=float(q.loc[('baseline',100),'initial_system_cost_usd_wp']),target_cost100=float(q.loc[('target',100),'initial_system_cost_usd_wp']),baseline_controller=q.loc[('baseline',100),'controlling_city'],target_controller=q.loc[('target',100),'controlling_city']))
pd.DataFrame(summary).to_csv(SD/'Figure4_displayed_decision_summary.csv',index=False,encoding='utf-8-sig')
js(Q/'Figure4_chain_checks.json',dict(status='PASS',regions=369,frontier_rows=len(f),coverage_grid_rows=len(g),threshold_rows=len(th),max_coverage_reconstruction_error_pp=maxcov,max_threshold_reconstruction_error_usd_wp=maxthreshold,financial_identities=len(ident),external_physical_numeric_records=len(external),inherited_source_data_unchanged=len(list((OLD/'Source_Data').glob('*.csv'))),prior_and_formal_files_unchanged=len(protected),Figures1_3_byte_identical=True,formal_manuscript_and_SI_unchanged=True,render=render))
doc=pymupdf.open()
for n in [1,2,3,4]:
 with pymupdf.open(O/f'Figure_{n}/Figure_{n}.pdf') as p:doc.insert_pdf(p)
doc.save(O/'Figures_1-4_common_start.pdf');doc.close()
report='''图4统一物理基线与经济覆盖门槛更新（2026-10-08，v19独立预览）

范围：图1–3与v18字节一致，保留地图及已有布局。图4保留两技术×两约束的四幅结构，50%/90%改为50%/100%，同图叠加图3运行路径起点与终点的成本—寿命边界。底色仅表示起点响应；黑线起点、技术色终点。25年列单独显示，不跨越更换跳变插值。正式正文、SI、图5及历史版本没有修改。图5尚未随共同物理基线更新，本轮不纳入合并预览。

计算：全部369地区，使用与当前图1–3完全相同的60点MPP物理结果、修正后的时间几何和空间算子。每项候选技术独立改善，另外两项技术保持共同起点；不暗示所有竞争技术同步发展。图3每条路径11个运行状态的经济覆盖均重算。经济基准为沿用的2035年作者成本与寿命情景，不是当前实测市场价格。成本、寿命与运行参数改善相互独立；寿命扫描内衰减、初损和持续/更换费用仍按原作者情景固定。50%取185/369的经验排序，100%取最受约束地区；不是置信区间。

已核对：121032条地区成本边界、65928条覆盖网格、656条覆盖门槛及1476条地区起终点经济变化。代回NPV最大残差约1.14e-13，起点与当前图1/图3发电量一致；旧财务代码在旧物理输入下可恢复旧边界。含平局的经济平价目标是另外两技术及不建设选项的最大NPV，不等于市场采用。

决策影响（成本、寿命、其他财务条件及竞争技术不变）：单结/装机163→174；单结/场地0→0；叠层/装机0→0；叠层/场地169→249。运行改善仍有单结35、叠层8个地区局部恶化；完整逐地区结果保留，不能用总计增加替代逐地区判断。经济全覆盖约束地区与图3物理补偿约束地区并不必然相同。

科学边界：在21.5年寿命、全额更换且无残值的主情景下，单结场地全覆盖逆算成本由-0.008647约改善至-0.004133 USD/Wp，均为负值，表示非负初始成本内不可达。这个结论并非器件固有或普遍不可达：半额更换或按剩余寿命计残值时，全覆盖允许成本变为正值。配套支持图明确展示该敏感性。不能把25年端点免除期内更换支出的跳变称为连续寿命收益。左/右列电价为0.04/0.08 USD/kWh，不能把列间变化全部归因于装机/场地约束；同价及0/25 USD/m²费用对照均保存。

溯源：重新从保存的国家能源局原DOCX表4核对33条2023/2024利用率原数，并核对369地区2024省内最小值映射；这不是机队利用小时。继承22条物理外源数值索引及原始资料SHA256，另给出30条财务参数身份和精确代码行。成本、学习种子、学习率、寿命、衰减、初损、电价、折现、更换与残值均按原作者情景或派生量记录，不冒充文献直接报告值。

复算顺序：工作区Python执行code/compute_figure4.py、code/verify_provenance.py、plot_figure4.py、plot_figure4_support.py、audit_and_build.py。物理上游无需再次逐小时模拟，输入已冻结并逐文件校验。原物理复算及气象逐值溯源仍保存在已核验统一起点包和v15完整溯源包。

导出：主图183×163mm；支持图183×155mm；可编辑PDF/SVG，PNG300dpi、TIFF600dpi。每次最终绘图后重新核对字体、对齐、碰撞、数据重建与跨版本保护。图4的形状及门槛图形仍为条件性模型结果。
'''
(O/'图4统一基线及决策影响更新记录.txt').write_text(report,encoding='utf-8')
def link(p,label):return '<a href="'+html.escape(p,quote=True)+'">'+html.escape(label)+'</a>'
def table(frame):return frame.to_html(index=False,border=0,escape=True)
labels={'single_junction':'单结','tandem':'叠层','capacity':'装机约束','site_area':'场地约束'}
display=pd.DataFrame([{'技术':labels[x['candidate']],'约束':labels[x['context']],'参考寿命（年）':x['life'],'竞争地区数':str(x['baseline_regions'])+' → '+str(x['target_regions']),'50%允许成本（美元/Wp）':f"{x['baseline_cost50']:.4f} → {x['target_cost50']:.4f}",'100%允许成本（美元/Wp）':f"{x['baseline_cost100']:.4f} → {x['target_cost100']:.4f}",'全覆盖约束地区':x['target_controller']} for x in summary])
style='body{font-family:Arial,"Microsoft YaHei",sans-serif;background:#f3f5f6;color:#26333c;margin:0;line-height:1.7}main{max-width:1150px;margin:28px auto;padding:0 24px}h1{font-size:25px}h2{font-size:20px}section{background:white;padding:23px 28px;border:1px solid #dfe5e9;border-radius:7px;margin:20px 0}img{display:block;width:100%;height:auto}a{color:#236c96;text-decoration:none}.links,nav{display:flex;flex-wrap:wrap;gap:18px}.small{color:#63727b;font-size:14px}summary{cursor:pointer}table{border-collapse:collapse;font-size:13px;width:100%}td,th{border-bottom:1px solid #e1e6e9;padding:9px;text-align:left}.scroll{overflow:auto}.compare{display:grid;grid-template-columns:1fr 1fr;gap:18px}@media(max-width:700px){.compare{grid-template-columns:1fr}}'
page='<!doctype html><html lang="zh"><meta charset="utf-8"><title>图4统一基线与经济覆盖 · v19</title><style>'+style+'</style><main><h1>图4：运行改善能兑现多少经济覆盖？</h1><p class="small">v19独立预览 · 保留四幅结构 · 统一物理起点 · 50%／100%门槛 · 图1–3不变</p><nav>'+''.join(link('#fig'+str(n),'图'+str(n)) for n in [1,2,3,4])+link('#support','财务与更换规则对照')+'</nav>'
page+='<section><p>图4比较图3起点与改善终点的经济后果，固定竞争技术、成本、寿命及财务条件；同图成本—寿命扫描仍是独立参数情景。底色为起点响应覆盖率，黑线为起点，橙／蓝线为各自路径终点；实线50%，虚线100%。</p><div class="links">'+link('Figures_1-4_common_start.pdf','四图合并PDF')+link('图4统一基线及决策影响更新记录.txt','完整更新记录')+link('qa/Figure4_chain_checks.json','一致性核对')+link('../Main_figures_preview_20261008_v14/index.html#fig4','旧图4对照')+'</div></section>'
for n in [1,2,3,4]:
 folder='Figure_'+str(n);cf=O/folder/(folder+('_caption_en.txt' if n in [3,4] else '_preview_caption.txt'))
 title={1:'图1｜紧凑版保持不变',2:'图2｜共同物理基线保持不变',3:'图3｜共同起点的物理补偿与运行路径',4:'图4｜经济覆盖门槛及路径改善影响'}[n]
 page+='<section id="fig'+str(n)+'"><h2>'+title+'</h2><img src="'+folder+'/'+folder+'.png" alt="图'+str(n)+'"><div class="links">'+''.join(link(folder+'/'+folder+'.'+e,e.upper()) for e in ['pdf','svg','tiff'])+link(str(cf.relative_to(O)).replace('\\','/'),'英文图注')+'</div><details><summary>图注</summary><p class="small">'+html.escape(cf.read_text(encoding='utf-8'))+'</p></details>'
 if n==4:
  page+='<div class="scroll">'+table(display)+'</div><p class="small">允许成本是满足相应覆盖目标的最高初始系统成本；负值表示非负成本内不可达。该不可达判断受全额更换、无残值规则约束，支持图给出替代规则。经济全覆盖约束地区与图3物理补偿约束地区不同。左右列电价也不同，约束比较需参考同价对照。</p>'
 page+='</section>'
folder='Figure_S_Fig4_decision_effects';cf=O/folder/(folder+'_caption.txt')
page+='<section id="support"><h2>配套支持｜经济路径、同价比较与更换规则</h2><img src="'+folder+'/'+folder+'.png" alt="图4配套支持"><p>更换规则改变了单结场地全覆盖的可达性；主图的不可达结论限于当前规则。支持图d用相同电价、零场地费比较约束，完整0／25美元每平方米费用对照另存源数据。</p><div class="links">'+link(folder+'/'+folder+'.pdf','PDF')+link('Source_Data/Figure4_matched_financial_controls.csv','全部同价与费用对照')+link('Source_Data/Figure4_replacement_boundary_sensitivity.csv','更换与残值敏感性')+link('Source_Data/Figure4_economic_path_summary.csv','全部11状态经济路径')+'</div><details><summary>支持图图注</summary><p class="small">'+html.escape(cf.read_text(encoding='utf-8'))+'</p></details></section>'
page+='<section><h2>源数据与数值溯源</h2><p>全部369地区保留。外源数值、作者情景和派生量分别记录；物理输入继承已核验的共同基线。正式正文、SI及历史版本未改动；图5尚未同步。</p><div class="links">'+''.join(link('Source_Data/'+f+'.csv',t) for f,t in [('Figure4_coverage_thresholds','50%／100%逐值门槛'),('Figure4_paired_region_economic_changes','逐地区起终点经济变化'),('Figure4_financial_parameter_identities','财务参数及精确代码位置'),('Figure4_official_utilization_numeric_locations','NEA原表逐值位置'),('Figure4_inherited_external_numeric_source_index','物理外源数值索引')])+link('qa/Figure4_provenance_checks.json','溯源及旧财务回归核对')+link('qa/Figure_4.collisions.json','主图碰撞核对')+link('qa/Figure_4.alignment.json','主图对齐核对')+link('../Main_figures_preview_20261008_v15/index.html','完整物理上游溯源')+link('../Common_start_paths_20261008/index.html','共同起点完整复算')+'</div></section></main></html>'
(O/'index.html').write_text(page,encoding='utf-8')
http=[]
for u in sorted(set(re.findall(r'(?:src|href)="([^"]+)"',page))):
 if u.startswith('#'):continue
 resource=urllib.parse.urldefrag(html.unescape(u))[0];url='http://127.0.0.1:8771/'+O.name+'/'+urllib.parse.quote(resource,safe='/?=&')
 with urllib.request.urlopen(url,timeout=10) as response:assert response.status==200;http.append(dict(resource=u,status=200))
js(Q/'gallery_http_check.json',dict(status='PASS',resources=http))
js(O/'delivery_manifest.json',{str(p.relative_to(O)).replace('\\','/'):sha(p) for p in O.rglob('*') if p.is_file() and p.name!='delivery_manifest.json' and '__pycache__' not in p.parts})
print('PASS: numerical chain, sources, all369 regions, font/alignment/collision gates, prior versions and gallery.',flush=True)
