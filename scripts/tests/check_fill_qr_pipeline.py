"""Small end-to-end fixture, including CSV quoting and invalid-bin retention."""
from pathlib import Path
import csv
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fill_qr import HEADER, Model, load_catalog, parser, generate
from validate_fill_qr import verify, sensitivities, charts_and_report


def write(path, header, rows):
    with path.open('w',encoding='utf-8',newline='') as f:
        writer=csv.writer(f);writer.writerow(header);writer.writerows(rows)


def main():
    d=Path('backend/data/validation/fill_qr_fixture');d.mkdir(parents=True,exist_ok=True)
    registry=d/'bins.csv';population=d/'population.csv';schedule=d/'schedule.csv'
    bins=[(1,1,'Mixed municipal waste',1.,'Verkių sen.','Daugiabučiai namai',100.),
          (2,2,'Glass waste',1.,'Antakalnis','Daugiabučiai namai',0.),
          (3,3,'Paper/plastic waste',1.,'Verkiai','Komercinė paskirtis',0.),
          (4,3,'Paper/plastic waste',3.,'Verkių sen.','Viešosios vietos',0.),
          (5,4,'Mixed municipal waste',1.,'Vilniaus','Daugiabučiai namai',100.),
          (6,5,'Mixed municipal waste',0.,'Verkiai','Komercinė paskirtis',0.),
          (7,6,'Mixed municipal waste',1.,'Verkiai','Unknown, quoted category',100.),
          (8,7,'Mixed municipal waste','NULL','Verkiai','Daugiabučiai namai',100.),
          (9,8,'Mixed municipal waste',1.,'Verkiai','Daugiabučiai namai','NULL')]
    write(registry,['id','site_id','waste_type','capacity_m3','sub_district','object_group'],[r[:6] for r in bins])
    write(population,['bin_id','population_cell_id','resident_factor'],[(r[0],1,r[6]) for r in bins])
    write(schedule,['id','bin_id','date'],[(i,i,'2026-10-01') for i in range(1,10)])
    catalog,_=load_catalog(registry,population,schedule);model=Model(catalog,'2026-10-01','2026-10-10')
    rows=[]
    statuses=['none','failed','collected','none','missed','retry_collected','none','failed','none','collected']
    for r in bins:
        for index,day in enumerate(model.dates):
            rows.append([r[0],str(day),day.isoweekday(),day.isocalendar().week,day.month,4,r[1],r[2],r[3],r[4],r[5],1,r[6],statuses[index],0,0,0])
    source=d/'source.csv';output=d/'enriched.csv';write(source,HEADER,rows)
    args=parser().parse_args(['--input',str(source),'--output',str(output),'--bins',str(registry),'--population',str(population),'--schedule',str(schedule),'--start','2026-10-01','--end','2026-10-10','--diagnostics',str(d),'--overwrite'])
    generate(args)
    result=verify(source,output,d,args)
    sensitivity=sensitivities(args)
    charts_and_report(args,result,sensitivity)
    assert result['rows_compared']==90
    assert result['nulls']['fill']==82
    print('Small pipeline fixture: PASS (90 rows, quoted values, 5 excluded bins including numeric NULLs, full diagnostics)')


if __name__=='__main__':main()
