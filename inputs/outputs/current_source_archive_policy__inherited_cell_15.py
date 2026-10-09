OUT=ROOT/'output'
curves=pd.DataFrame([dict(stage='S0',context=ctx,**policy_result(options[('S0',ctx)],strategy,float(share))[0]) for ctx in ['capacity','area'] for strategy in ['General','New technology','Matched gap'] for share in np.linspace(0,0.3,301)])
summary=summary[summary.stage=='S0'].copy()
details=details[details.stage=='S0'].copy()
for frame in [curves,summary]:
    frame['direct_support_usd']=frame.direct_public_usd+np.where(frame.strategy=='Matched gap',frame.new_viable+frame.material_switches,0)
    frame['admin_usd']=0.05*frame.direct_support_usd
    frame['total_public_usd']=frame.direct_support_usd+frame.admin_usd
    frame.drop(columns=['stage','direct_public_usd']).to_csv(OUT/('Figure5_policy_curves.csv' if frame is curves else 'Figure5_policy_summary.csv'),index=False)
details.loc[(details.strategy=='Matched gap') & (details.before_choice!=details.after_choice),'grant_usd'] += 1
details.drop(columns='stage').to_csv(OUT/'Figure5_policy_city.csv',index=False)
baseline[baseline.stage=='S0'].drop(columns='stage').to_csv(OUT/'Figure5_baseline_options.csv',index=False)
selected_stages=['S0']
