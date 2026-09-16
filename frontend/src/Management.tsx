import React,{useState} from 'react';
import {useQuery,useQueryClient} from '@tanstack/react-query';
import {NavLink} from 'react-router-dom';
import {api} from './api';
import {Empty,ErrorState,Skeleton} from './components';

const templates:Record<string,Record<string,any>>={
  clinics:{name:'',code:'',city:'',active:true},
  laboratories:{name:'',code:'',country:'IL',active:true},
  analytes:{code:'',display_name_he:'',display_name_en:'',category:'CBC',description_he:'',typical_unit:'',comparison_direction:'RANGE',active:true},
  'reference-ranges':{analyte_id:1,laboratory_id:null,sex:null,age_min:null,age_max:null,unit:'',min_value:0,max_value:1,valid_from:null,valid_to:null,source_reference:'',active:true},
  'critical-thresholds':{analyte_id:1,laboratory_id:1,unit:'',low_value:null,high_value:null,source_reference:'',active:false},
  recommendations:{rule_code:'',title_he:'',content_he:'',severity:'INFO',evidence_source:'',active:true},
};
const names:Record<string,string>={clinics:'מרפאות',laboratories:'מעבדות',analytes:'מדדים','reference-ranges':'טווחי ייחוס','critical-thresholds':'ספים קריטיים',recommendations:'כללי המלצה'};
const labels:Record<string,string>={name:'שם',code:'קוד',city:'עיר',country:'מדינה',active:'פעיל',display_name_he:'שם בעברית',display_name_en:'שם באנגלית',category:'קטגוריה',description_he:'הסבר בעברית',typical_unit:'יחידה',comparison_direction:'בסיס השוואה',analyte_id:'מדד',laboratory_id:'מעבדה',sex:'מין ביולוגי',age_min:'גיל מינימלי',age_max:'גיל מקסימלי',unit:'יחידה',min_value:'גבול תחתון',max_value:'גבול עליון',valid_from:'בתוקף מתאריך',valid_to:'בתוקף עד',source_reference:'מקור מאומת',low_value:'סף נמוך',high_value:'סף גבוה',rule_code:'קוד כלל',title_he:'כותרת',content_he:'תוכן',severity:'חומרה',evidence_source:'מקור'};
type CatalogRow=Record<string,any>;

// Reference ranges and critical thresholds store only analyte_id and
// laboratory_id. These turn the ids into the names an admin recognises.
function catalogLookups(analytes:CatalogRow[]=[],laboratories:CatalogRow[]=[]){
  const analyteById=new Map(analytes.map(a=>[a.id,a]));
  const labById=new Map(laboratories.map(l=>[l.id,l]));
  const analyteName=(id:number)=>analyteById.get(id)?.display_name_he??`מדד ${id}`;
  const labName=(id:number|null)=>id==null?'כל המעבדות':labById.get(id)?.name??`מעבדה ${id}`;
  return {analyteById,labById,analyteName,labName};
}

function formatBound(low:number|null,high:number|null,unit:string){
  if(low!=null&&high!=null) return `${low}–${high} ${unit}`;
  if(low!=null) return `מעל ${low} ${unit}`;
  if(high!=null) return `עד ${high} ${unit}`;
  return unit;
}

function CatalogRecord({resource,row,lookups}:{resource:string;row:CatalogRow;lookups:ReturnType<typeof catalogLookups>}){
  if(resource==='reference-ranges'||resource==='critical-thresholds'){
    const analyte=lookups.analyteById.get(row.analyte_id);
    const bounds=resource==='reference-ranges'
      ?formatBound(row.min_value,row.max_value,row.unit)
      :`סף נמוך ${row.low_value??'—'} · סף גבוה ${row.high_value??'—'} ${row.unit}`;
    return <div className="py-2">
      <div className="font-bold">{lookups.analyteName(row.analyte_id)}{analyte&&<span className="mr-2 text-xs font-normal text-slate-500" dir="ltr">{analyte.code}</span>}</div>
      <div className="text-sm text-slate-600"><span dir="ltr">{bounds}</span> · {lookups.labName(row.laboratory_id)}</div>
      {row.source_reference&&<div className="text-xs text-slate-400">{row.source_reference}</div>}
    </div>;
  }
  if(resource==='analytes') return <span><b>{row.display_name_he}</b> <span className="text-sm text-slate-500" dir="ltr">{row.code} · {row.typical_unit}</span></span>;
  return <span>{row.name||row.title_he}</span>;
}

export function UsersPanel(){
  const qc=useQueryClient();
  const [open,setOpen]=useState(false);
  const [error,setError]=useState('');
  const [created,setCreated]=useState<{email:string;role:string}|null>(null);
  const users=useQuery({queryKey:['users'],queryFn:()=>api.users()});
  const clinics=useQuery({queryKey:['clinics'],queryFn:()=>api.clinics()});
  const roleName:Record<string,string>={ADMIN:'מנהל מערכת',DOCTOR:'רופא',CLINIC:'מרפאה',PATIENT:'מטופל'};

  const submit=async(event:React.FormEvent<HTMLFormElement>)=>{
    event.preventDefault();
    setError('');
    const form=new FormData(event.currentTarget);
    const role=String(form.get('role'));
    const clinicValue=form.get('clinic_id');
    try{
      const body={
        email:String(form.get('email')).trim().toLowerCase(),
        password:String(form.get('password')),
        role,
        clinic_id:role==='DOCTOR'||role==='CLINIC'?Number(clinicValue):null,
      };
      const row=await api.createUser(body);
      setCreated({email:row.email,role:row.role});
      setOpen(false);
      await qc.invalidateQueries({queryKey:['users']});
    }catch(e){setError((e as Error).message)}
  };

  return <div className="mb-8">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 className="text-xl font-bold">משתמשים</h2>
        <p className="mt-1 text-sm text-slate-500">
          יצירת חשבונות לרופאים, למרפאות ולמנהלים. רופא ומרפאה חייבים להיות משויכים למרפאה.
        </p>
      </div>
      <button className="btn-primary" onClick={()=>{setOpen(!open);setCreated(null)}}>
        {open?'ביטול':'משתמש חדש'}
      </button>
    </div>

    {created&&<div className="card mt-4 border-2 border-brand-600 p-4">
      <b>נוצר משתמש חדש</b>
      <p className="mt-1 text-sm">{created.email} · {roleName[created.role]||created.role}</p>
      <p className="mt-2 text-sm text-slate-600">
        הכניסה מתבצעת עם סיסמת ההדגמה המשותפת שהוגדרה במערכת.
      </p>
    </div>}

    {error&&<div role="alert" className="mt-4 rounded-xl bg-red-50 p-3 text-sm text-red-800">{error}</div>}

    {open&&<form className="card mt-4 grid gap-4 p-5 md:grid-cols-2" onSubmit={submit}>
      <label>
        <span className="label">כתובת דוא״ל</span>
        <input className="field" name="email" type="email" required dir="ltr"/>
      </label>
      <label>
        <span className="label">תפקיד</span>
        <select className="field" name="role" required defaultValue="DOCTOR">
          <option value="DOCTOR">רופא</option>
          <option value="CLINIC">מרפאה</option>
          <option value="ADMIN">מנהל מערכת</option>
        </select>
      </label>
      <label>
        <span className="label">מרפאה (לרופא ולמרפאה)</span>
        <select className="field" name="clinic_id" defaultValue="">
          <option value="">ללא</option>
          {(clinics.data||[]).map(c=><option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
      </label>
      <label>
        <span className="label">סיסמה</span>
        <input className="field" name="password" type="text" defaultValue="Hemora123!" minLength={8} required dir="ltr"/>
        <span className="mt-1 block text-xs text-slate-500">
          במערכת ההדגמה משתמשים בסיסמה אחידה לכל החשבונות.
        </span>
      </label>
      <div className="md:col-span-2"><button className="btn-primary">יצירת משתמש</button></div>
    </form>}

    <div className="card mt-4 overflow-auto">
      <table className="w-full text-right text-sm">
        <thead className="bg-slate-50">
          <tr><th className="p-3">דוא״ל</th><th>תפקיד</th><th>מרפאה</th><th>מצב</th></tr>
        </thead>
        <tbody>
          {(users.data||[]).map(u=><tr className="border-t" key={u.id}>
            <td className="p-3" dir="ltr">{u.email}</td>
            <td>{roleName[u.role]||u.role}</td>
            <td>{(clinics.data||[]).find(c=>c.id===u.clinic_id)?.name||'—'}</td>
            <td>פעיל</td>
          </tr>)}
        </tbody>
      </table>
    </div>
  </div>;
}

export function Management(){
  const [resource,setResource]=useState('laboratories');const [draft,setDraft]=useState<Record<string,any>|null>(null);const [error,setError]=useState('');const qc=useQueryClient();
  const q=useQuery({queryKey:['config',resource],queryFn:()=>api.config(resource)});
  const analytes=useQuery({queryKey:['config','analytes'],queryFn:()=>api.config('analytes')});
  const laboratories=useQuery({queryKey:['config','laboratories'],queryFn:()=>api.config('laboratories')});
  const lookups=catalogLookups(analytes.data,laboratories.data);
  const referenceField=(key:string,value:any)=>{
    if(!draft) return null;
    if(key==='analyte_id') return <select className="field" value={value??''} onChange={e=>{const id=Number(e.target.value);setDraft({...draft,analyte_id:id,unit:draft.unit||lookups.analyteById.get(id)?.typical_unit||''})}}>
      {(analytes.data||[]).map(a=><option key={a.id} value={a.id}>{a.display_name_he} ({a.code} · {a.typical_unit})</option>)}
    </select>;
    return <select className="field" value={value??''} onChange={e=>setDraft({...draft,laboratory_id:e.target.value===''?null:Number(e.target.value)})}>
      {resource==='reference-ranges'&&<option value="">כל המעבדות</option>}
      {(laboratories.data||[]).map(l=><option key={l.id} value={l.id}>{l.name}</option>)}
    </select>;
  };
  const audit=useQuery({queryKey:['audit'],queryFn:api.audit});
  const save=async()=>{if(!draft)return;try{const {id,...body}=draft;await api.saveConfig(resource,body,id);setDraft(null);setError('');await qc.invalidateQueries({queryKey:['config']});await qc.invalidateQueries({queryKey:['audit']});}catch(e){setError((e as Error).message)}};
  return <div><h1 className="mb-6 text-3xl font-black">ניהול וביקורת</h1><UsersPanel/><h2 className="text-xl font-bold">קטלוג המערכת</h2><div className="my-5 flex flex-wrap gap-2">{Object.entries(names).map(([key,label])=><button className={key===resource?'btn-primary':'btn-soft'} key={key} onClick={()=>{setResource(key);setDraft(null)}}>{label}</button>)}</div><button className="btn-primary mb-4" onClick={()=>setDraft({...templates[resource]})}>הוספת רשומה</button>{error&&<ErrorState message={error}/>} {draft&&<form className="card mb-5 grid gap-4 p-5 md:grid-cols-3" onSubmit={e=>{e.preventDefault();save()}}>{Object.entries(draft).filter(([key])=>key!=='id').map(([key,value])=><label key={key}><span className="label">{labels[key]||key}</span>{typeof value==='boolean'?<input type="checkbox" checked={value} onChange={e=>setDraft({...draft,[key]:e.target.checked})}/>:key==='analyte_id'||key==='laboratory_id'?referenceField(key,value):<input className="field" value={value??''} onChange={e=>{const raw=e.target.value;const numeric=['analyte_id','laboratory_id','age_min','age_max','min_value','max_value','low_value','high_value'].includes(key);setDraft({...draft,[key]:raw===''?null:numeric?Number(raw):raw})}}/>}</label>)}<div className="flex gap-2"><button className="btn-primary">שמירה</button><button type="button" className="btn-soft" onClick={()=>setDraft(null)}>ביטול</button></div></form>}{q.isLoading?<Skeleton/>:q.error?<ErrorState message={(q.error as Error).message}/>:<div className="card overflow-auto"><table className="w-full text-right"><thead><tr><th className="p-3">מזהה</th><th>רשומה</th><th>מצב</th><th>פעולה</th></tr></thead><tbody>{q.data?.map(row=><tr className="border-t" key={row.id}><td className="p-3">{row.id}</td><td><CatalogRecord resource={resource} row={row} lookups={lookups}/></td><td>{row.active?'פעיל':'לא פעיל'}</td><td><button className="btn-soft" onClick={()=>setDraft({...row})}>עריכה</button></td></tr>)}</tbody></table></div>}<h2 className="my-5 text-xl font-bold">יומן ביקורת</h2><div className="card overflow-auto"><table className="w-full text-right"><tbody>{audit.data?.map(row=><tr className="border-b" key={row.id}><td className="p-3">{new Date(row.timestamp).toLocaleString('he-IL')}</td><td>{row.action}</td><td>{row.entity_type}</td><td>{row.user_id}</td></tr>)}</tbody></table></div></div>;
}
export function AlertCenter(){const qc=useQueryClient();const [error,setError]=useState('');const q=useQuery({queryKey:['alerts'],queryFn:api.alerts});return <div><h1 className="mb-6 text-3xl font-black">מרכז התראות</h1>{error&&<ErrorState message={error}/>} {q.isLoading?<Skeleton/>:q.error?<ErrorState message={(q.error as Error).message}/>:!q.data?.length?<Empty title="אין התראות" body="התראות נוצרות מניתוח נתוני הבדיקות."/>:<div className="space-y-3">{q.data.map(a=><div className="card p-5" key={a.id}><h2 className="font-bold">{a.title_he}</h2><p className="my-2">{a.state==='NEW'?'חדש':a.state==='READ'?'נקרא':'טופל'}</p><div className="flex gap-2"><NavLink className="btn-soft" to={`/tests/${a.test_id}`}>פתיחת בדיקה</NavLink>{['READ','RESOLVED'].map(state=><button className="btn-soft" disabled={a.state===state} key={state} onClick={async()=>{try{await api.setAlert(a.id,state);await qc.invalidateQueries({queryKey:['alerts']})}catch(e){setError((e as Error).message)}}}>{state==='READ'?'סימון כנקרא':'סימון כטופל'}</button>)}</div></div>)}</div>}</div>}
