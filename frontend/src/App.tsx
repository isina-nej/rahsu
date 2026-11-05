import { useEffect, useRef, useState } from 'react';
import maplibregl, { type Map as MapType, type GeoJSONSource } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { AlertTriangle, CarFront, CheckCircle2, Fuel, MapPin, RotateCcw, ShieldCheck, SlidersHorizontal, TrafficCone } from 'lucide-react';

type Point = {lat:number;lon:number};
type SessionInfo={authenticated:boolean;username:string;staff:boolean;signup_enabled:boolean};
type PendingReport={id:number;action:string;kind:string;lat:number;lon:number;road_name:string;direction:string;status:string;note:string};
type Place = Point & {label:string};
type Obstacle = {id:number;kind:string;lon:number;lat:number;source:string;verified:boolean;road_name:string};
type Route = {
  prediction_id:number|null;
  index:number; distance_m:number; osrm_duration_s:number; modeled_duration_s:number;
  estimated_l:number;estimated_range_l:number[];baseline_l:number;
  idle_l:number;propulsion_l:number;warnings:string[];
  obstacle_summary:{nearby:number;reviewed_applied:number;topology_matched_osm_calming?:number;total_applied?:number;signals_scenario:number;stops:number;slowdowns:number};
  terrain:{ascent_m:number;descent_m:number}|null;
  model_version:string;geometry:{type:'LineString';coordinates:number[][]}
};
type EstimateResponse={routes:Route[];research_only:boolean};
const API=import.meta.env.VITE_API_BASE_URL || '';
const TEHRAN:[number,number]=[51.389,35.6892];
const LIMIT={minLon:51.05,maxLon:51.75,minLat:35.45,maxLat:35.95};
const labels:Record<string,string>={
  bump:'سرعت‌گیر',hump:'دست‌انداز',traffic_signals:'چراغ راهنمایی',
  stop:'تابلو ایست',crossing:'گذرگاه عابر',other:'مانع دیگر'
};
const warnings:Record<string,string>={
  uncalibrated_for_pride:'ضرایب مدل هنوز با سفرهای واقعی پراید کالیبره نشده‌اند.',
  traffic_not_live:'ترافیک زنده در محاسبه استفاده نشده است.',
  grade_not_measured:'اطلاعات ارتفاع مسیر موجود نیست؛ شیب در محاسبه لحاظ نشده است.',
  grade_provider_unavailable:'سرویس ارتفاع در دسترس نیست.',
  signal_red_probability_is_assumed:'احتمال قرمز بودن چراغ فرضی است.',
  unreviewed_osm_not_applied:'موانع بدون تطبیق معتبر روی مسیر وارد محاسبه نشده‌اند.',
  osm_signals_stops_require_direction_review:'چراغ‌های راهنمایی و تابلوهای ایست OSM به تأیید جهت حرکت نیاز دارند.',
  manual_obstacle_matching_is_conservative:'تطبیق موانع با مسیر محافظه‌کارانه است.',
  idealized_engine_and_drive_cycle:'مدل موتور و الگوی حرکت ساده‌سازی شده‌اند.',
  dem_resolution_limited:'داده ارتفاع محدودیت تفکیک مکانی دارد.'
};
const faNum=(num:number,digits=1)=>num.toLocaleString('fa-IR',{maximumFractionDigits:digits,minimumFractionDigits:digits});
const typeColor=(o:Obstacle)=>o.verified?'#1b866c':'#ee973a';
const within=(p:Point)=>p.lat>=LIMIT.minLat&&p.lat<=LIMIT.maxLat&&p.lon>=LIMIT.minLon&&p.lon<=LIMIT.maxLon;

export default function App(){
  const mapNode=useRef<HTMLDivElement>(null);
  const map=useRef<MapType|null>(null);
  const points=useRef<{origin:Point|null;destination:Point|null}>({origin:null,destination:null});
  const sessionRef=useRef<SessionInfo>({authenticated:false,username:'',staff:false,signup_enabled:false});
  const [origin,setOrigin]=useState<Point|null>(null),[destination,setDestination]=useState<Point|null>(null);
  const [routes,setRoutes]=useState<Route[]>([]),[selected,setSelected]=useState(0);
  const [obstacles,setObstacles]=useState<Obstacle[]>([]);
  const [obstacleWarning,setObstacleWarning]=useState('');
  const reportMode=useRef(false);
  const [reportPoint,setReportPoint]=useState<Point|null>(null);
  const [reportObstacleId,setReportObstacleId]=useState<number|null>(null);
  const [reportAction,setReportAction]=useState('add');
  const [reportKind,setReportKind]=useState('bump');
  const [reportRoad,setReportRoad]=useState('');
  const [reportDirection,setReportDirection]=useState('unknown');
  const [reportNote,setReportNote]=useState('');
  const [reportMessage,setReportMessage]=useState('');
  const [pendingReports,setPendingReports]=useState<PendingReport[]>([]);
  const [passengers,setPassengers]=useState(1),[ac,setAc]=useState(false),[cargo,setCargo]=useState(0);
  const [redProbability,setRedProbability]=useState(0.5);
  const [saveHistory,setSaveHistory]=useState(false);
  const [session,setSession]=useState<SessionInfo>({authenticated:false,username:'',staff:false,signup_enabled:false});
  useEffect(()=>{sessionRef.current=session;},[session]);
  const [username,setUsername]=useState(''),[password,setPassword]=useState('');
  const [authBusy,setAuthBusy]=useState(false),[authError,setAuthError]=useState('');
  const [observedFuel,setObservedFuel]=useState(''),[observedDistance,setObservedDistance]=useState('');
  const [observationMethod,setObservationMethod]=useState('obd');
  const [consent,setConsent]=useState(false),[observationMessage,setObservationMessage]=useState('');
  const [originText,setOriginText]=useState(''),[destText,setDestText]=useState('');
  const [places,setPlaces]=useState<Place[]>([]);
  const [placeTarget,setPlaceTarget]=useState<'origin'|'destination'>('origin');
  const [geocodeBusy,setGeocodeBusy]=useState(false);
  const [error,setError]=useState(''),[busy,setBusy]=useState(false);

  useEffect(()=>{
    let live=true;
    fetch(API+'/api/v1/auth/me/',{credentials:'same-origin'})
      .then(r=>r.json()).then((s:SessionInfo)=>{if(live)setSession(s);})
      .catch(()=>{});
    return()=>{live=false;};
  },[]);

  const csrf=async()=>{
    const r=await fetch(API+'/api/v1/auth/csrf/',{credentials:'same-origin'});
    if(!r.ok)throw new Error('خطای دریافت CSRF');
    const data=await r.json() as {csrfToken:string};
    return data.csrfToken;
  };
  const signIn=async(mode:'login'|'register')=>{
    if(authBusy)return;setAuthBusy(true);setAuthError('');
    try{
      const token=await csrf();
      const response=await fetch(API+'/api/v1/auth/'+mode+'/',{method:'POST',
        credentials:'same-origin',
        headers:{'Content-Type':'application/json','X-CSRFToken':token},
        body:JSON.stringify({username,password})});
      const body=await response.json() as {authenticated?:boolean;error?:string;username?:string};
      if(!response.ok)throw new Error(body.error==='invalid_credentials'?
        'نام کاربری یا رمز عبور نامعتبر است.':body.error||'ورود انجام نشد.');
      const current=await fetch(API+'/api/v1/auth/me/',{credentials:'same-origin'});
      setSession(await current.json() as SessionInfo);
      setPassword('');
    }catch(e){setAuthError(e instanceof Error?e.message:'خطا در ورود');}
    finally{setAuthBusy(false);}
  };
  const signOut=async()=>{
    try{
      const token=await csrf();
      await fetch(API+'/api/v1/auth/logout/',{method:'POST',credentials:'same-origin',
        headers:{'X-CSRFToken':token}});
    }finally{setSaveHistory(false);setRoutes([]);
      setSession(s=>({...s,authenticated:false,username:'',staff:false}));}
  };

  const submitObservation=async()=>{
    const route=routes[selected];
    if(!route?.prediction_id||!consent){setObservationMessage('تأیید رضایت و ذخیره مسیر الزامی است.');return;}
    const distance=Number(observedDistance);
    const fuel=Number(observedFuel);
    if(!(distance>=100&&distance<=100000&&fuel>0&&fuel<=30)){
      setObservationMessage('مسافت واقعی و لیتر مصرف‌شده را درست وارد کنید.');return;}
    setObservationMessage('');
    try{
      const token=await csrf();
      const response=await fetch(API+'/api/v1/trips/observations/',{
        method:'POST',credentials:'same-origin',
        headers:{'Content-Type':'application/json','X-CSRFToken':token},
        body:JSON.stringify({prediction_id:route.prediction_id,distance_m:distance,
          observed_fuel_l:fuel,method:observationMethod,consent_given:consent})
      });
      const body=await response.json() as {error?:string};
      if(!response.ok)throw new Error(body.error||'ثبت ناموفق بود');
      setObservationMessage('اندازه‌گیری ثبت شد. از مشارکت در اعتبارسنجی سپاسگزاریم.');
      setObservedDistance('');setObservedFuel('');setConsent(false);
    }catch(e){setObservationMessage(e instanceof Error?e.message:'خطای ثبت اندازه‌گیری');}
  };

  useEffect(()=>{
    if(!mapNode.current)return;
    const m=new maplibregl.Map({container:mapNode.current,
      style:import.meta.env.VITE_MAP_STYLE_URL||'https://tiles.openfreemap.org/styles/liberty',
      center:TEHRAN,zoom:11});
    m.addControl(new maplibregl.NavigationControl(),'top-left');
    let controller:AbortController|null=null;
    const fetchVisible=async()=>{
      const bounds=m.getBounds();
      const rect=[
        Math.max(LIMIT.minLon,bounds.getWest()),
        Math.max(LIMIT.minLat,bounds.getSouth()),
        Math.min(LIMIT.maxLon,bounds.getEast()),
        Math.min(LIMIT.maxLat,bounds.getNorth())
      ];
      if(rect[0]>=rect[2]||rect[1]>=rect[3])return;
      controller?.abort();controller=new AbortController();
      try{
        const result=await fetch(API+'/api/v1/obstacles/?bbox='+rect.join(','),{signal:controller.signal});
        if(!result.ok)throw new Error('Obstacle API unavailable');
        const body=await result.json() as {results:Obstacle[];truncated:boolean};
        setObstacles(body.results||[]);
        setObstacleWarning(body.truncated?'تعداد موانع این محدوده زیاد است؛ برای مشاهده جزئیات بیشتر بزرگ‌نمایی کنید.':'');
      }catch(e){if(!(e instanceof DOMException&&e.name==='AbortError'))setObstacleWarning('دریافت موانع نقشه در دسترس نیست.');}
    };
    m.on('load',fetchVisible);m.on('moveend',fetchVisible);
    m.on('click',(ev)=>{
      if(m.getLayer('obstacles')&&m.queryRenderedFeatures(ev.point,{layers:['obstacles']}).length)return;
      const p={lat:ev.lngLat.lat,lon:ev.lngLat.lng};
      if(!within(p)){setError('لطفاً نقطه‌ای در محدوده تهران انتخاب کنید.');return;}
      if(reportMode.current){
        reportMode.current=false;setReportPoint(p);setReportObstacleId(null);
        setReportAction('add');setReportMessage('محل مانع انتخاب شد.');
        return;
      }
      setError('');setRoutes([]);
      const next=points.current.origin&&!points.current.destination?'destination':'origin';
      if(next==='origin'){
        points.current={origin:p,destination:null};setOrigin(p);setDestination(null);
      }else{points.current.destination=p;setDestination(p);}
    });
    m.on('click','obstacles',(ev)=>{
      const feature=ev.features?.[0];if(!feature||feature.geometry.type!=='Point')return;
      const p=feature.properties||{};
      if(sessionRef.current.authenticated){
        setReportPoint({lat:feature.geometry.coordinates[1],lon:feature.geometry.coordinates[0]});
        setReportObstacleId(Number(p.id));setReportAction('correct');
        setReportKind(String(p.kind));setReportMessage('مانع روی نقشه انتخاب شد؛ اصلاح یا حذف را مشخص کنید.');
      }
      new maplibregl.Popup({closeButton:true}).setLngLat(feature.geometry.coordinates as [number,number])
        .setText((labels[String(p.kind)]||'مانع')+' — '+(p.verified?'تأییدشده':'از نقشه، نیازمند بررسی'))
        .addTo(m);
    });
    map.current=m;
    return()=>{controller?.abort();m.remove();map.current=null};
  },[]);

  useEffect(()=>{
    const m=map.current;if(!m)return;
    const markers:maplibregl.Marker[]=[];
    for(const [point,color] of [[origin,'#15876a'],[destination,'#e06e45']] as const){
      if(point)markers.push(new maplibregl.Marker({color}).setLngLat([point.lon,point.lat]).addTo(m));
    }
    return()=>markers.forEach(x=>x.remove());
  },[origin,destination]);

  useEffect(()=>{
    const m=map.current;if(!m)return;
    const update=()=>{
      if(!m.isStyleLoaded())return;
      const featureCollection={
        type:'FeatureCollection' as const,
        features:obstacles.map(o=>({
          type:'Feature' as const,
          properties:{id:o.id,kind:o.kind,verified:o.verified,color:typeColor(o)},
          geometry:{type:'Point' as const,coordinates:[o.lon,o.lat]}
        }))
      };
      const src=m.getSource('obstacles') as GeoJSONSource|undefined;
      if(src)src.setData(featureCollection);
      else{
        m.addSource('obstacles',{type:'geojson',data:featureCollection});
        m.addLayer({id:'obstacles',type:'circle',source:'obstacles',
          paint:{'circle-color':['get','color'],'circle-radius':5,
          'circle-stroke-color':'#fff','circle-stroke-width':1.3,'circle-opacity':0.88}});
      }
    };
    if(m.isStyleLoaded())update();else m.once('load',update);
  },[obstacles]);

  useEffect(()=>{
    const m=map.current;if(!m)return;
    const update=()=>{
      if(!m.isStyleLoaded())return;
      const route=routes[selected];
      const feature={type:'Feature' as const,properties:{},geometry:route?.geometry||
        {type:'LineString' as const,coordinates:[]}};
      const src=m.getSource('rahsu-route') as GeoJSONSource|undefined;
      if(src)src.setData(feature);
      else{
        m.addSource('rahsu-route',{type:'geojson',data:feature});
        m.addLayer({id:'rahsu-route',type:'line',source:'rahsu-route',
          paint:{'line-color':'#1764c0','line-width':6,'line-opacity':.88}});
      }
      if(route&&route.geometry.coordinates.length>=2){
        const bounds=new maplibregl.LngLatBounds(
          route.geometry.coordinates[0] as [number,number],
          route.geometry.coordinates[0] as [number,number]);
        for(const point of route.geometry.coordinates)bounds.extend(point as [number,number]);
        m.fitBounds(bounds,{padding:65,maxZoom:15});
      }
    };
    if(m.isStyleLoaded())update();else m.once('load',update);
  },[routes,selected]);

  const submitObstacle=async()=>{
    if(!reportPoint||!session.authenticated){setReportMessage('ابتدا وارد حساب شوید و نقطه را مشخص کنید.');return;}
    setReportMessage('');
    try{
      const token=await csrf();
      const response=await fetch(API+'/api/v1/obstacle-reports/',{
        method:'POST',credentials:'same-origin',
        headers:{'Content-Type':'application/json','X-CSRFToken':token},
        body:JSON.stringify({action:reportAction,kind:reportKind,lat:reportPoint.lat,
          lon:reportPoint.lon,road_name:reportRoad,direction:reportDirection,
          note:reportNote,...(reportAction==='add'?{}:{obstacle_id:reportObstacleId})})
      });
      const result=await response.json() as {error?:string};
      if(!response.ok)throw new Error(result.error||'ارسال گزارش ناموفق بود');
      setReportMessage('گزارش با موفقیت ثبت شد و در صف بررسی مدیر است.');
      setReportPoint(null);setReportObstacleId(null);setReportNote('');
    }catch(e){setReportMessage(e instanceof Error?e.message:'خطای ارسال');}
  };
  const refreshPending=async()=>{
    try{
      const response=await fetch(API+'/api/v1/admin/obstacle-reports/',{credentials:'same-origin'});
      if(!response.ok)throw new Error('خطای دسترسی به گزارش‌ها');
      const data=await response.json() as {results:PendingReport[]};
      setPendingReports(data.results||[]);
    }catch(e){setReportMessage(e instanceof Error?e.message:'خطای دریافت گزارش‌ها');}
  };
  const decidePending=async(id:number,decision:'approve'|'reject')=>{
    try{
      const token=await csrf();
      const response=await fetch(API+'/api/v1/admin/obstacle-reports/',{
        method:'PATCH',credentials:'same-origin',
        headers:{'Content-Type':'application/json','X-CSRFToken':token},
        body:JSON.stringify({id,decision})});
      if(!response.ok)throw new Error('ثبت تصمیم مدیر ناموفق بود.');
      await refreshPending();
    }catch(e){setReportMessage(e instanceof Error?e.message:'خطا');}
  };
  const choosePlace=(p:Place,target:'origin'|'destination')=>{
    if(!within(p)){setError('نتیجه انتخابی خارج از محدوده تهران است.');return;}
    if(target==='origin'){points.current.origin=p;setOrigin(p);setOriginText(p.label);}
    else{points.current.destination=p;setDestination(p);setDestText(p.label);}
    setRoutes([]);setPlaces([]);setError('');
    map.current?.flyTo({center:[p.lon,p.lat],zoom:14});
  };
  const geocode=async(target:'origin'|'destination')=>{
    const q=(target==='origin'?originText:destText).trim();
    if(q.length<2)return;setPlaceTarget(target);setGeocodeBusy(true);setPlaces([]);setError('');
    try{
      const response=await fetch(API+'/api/v1/geocode/?q='+encodeURIComponent(q));
      const body=await response.json() as {results?:Place[];error?:string};
      if(!response.ok)throw new Error(body.error==='geocoder_not_configured'?
        'جست‌وجوی آدرس روی سرور تنظیم نشده؛ از انتخاب نقطه روی نقشه استفاده کنید.':
        'خدمات جست‌وجوی آدرس در دسترس نیست.');
      setPlaces(body.results||[]);
      if(!body.results?.length)setError('آدرسی در محدوده تهران پیدا نشد.');
    }catch(e){setError(e instanceof Error?e.message:'خطا در جست‌وجو');}
    finally{setGeocodeBusy(false);}
  };
  const reset=()=>{points.current={origin:null,destination:null};
    setOrigin(null);setDestination(null);setRoutes([]);setError('');};
  const run=async()=>{
    if(!origin||!destination)return;setBusy(true);setError('');setRoutes([]);
    try{
      const response=await fetch(API+'/api/v1/estimates/',{
        method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({origin,destination,passengers,cargo_kg:cargo,ac_on:ac,
          signal_red_probability:redProbability,save_history:saveHistory&&session.authenticated})
      });
      const body=await response.json() as EstimateResponse&{error?:string};
      if(!response.ok)throw new Error(
        body.error==='routing_provider_unavailable'?'OSRM در دسترس نیست؛ داده واقعی تهران باید راه‌اندازی شود.':
        body.error==='no_route'?'مسیر رانندگی بین این دو نقطه پیدا نشد.':
        body.error||'خطا در تخمین مسیر');
      if(!body.routes?.length)throw new Error('مسیر قابل محاسبه‌ای دریافت نشد.');
      setRoutes(body.routes);
      setSelected(body.routes.reduce((best,item,index,all)=>
        item.estimated_l<all[best].estimated_l?index:best,0));
    }catch(e){setError(e instanceof Error?e.message:'خطای ارتباط با سرور');}
    finally{setBusy(false);}
  };
  const active=routes[selected];
  return <div className="layout" dir="rtl">
    <aside className="sidebar">
      <header>
        <span className="brand"><CarFront size={25}/> راه‌سو</span>
        <small>تخمین پژوهشی مصرف بنزین پراید در تهران</small>
      </header>
      <section className="auth-box"><h2><ShieldCheck size={17}/> حساب پژوهشی</h2>
      {session.authenticated?
        <div className="auth-signed"><span>ورود به‌عنوان {session.username}</span>
          <button className="text-button" onClick={()=>void signOut()}>خروج</button></div>
        :<><p>برای ثبت مسیر و سوخت واقعی، وارد شوید. محاسبه بدون حساب هم ممکن است.</p>
          <div className="inputs-two">
            <label>نام کاربری<input value={username} autoComplete="username" onChange={e=>setUsername(e.target.value)}/></label>
            <label>رمز عبور<input type="password" value={password} autoComplete="current-password"
              onChange={e=>setPassword(e.target.value)}/></label>
          </div>
          <div className="auth-actions">
            <button disabled={authBusy||!username||!password} onClick={()=>void signIn('login')}>ورود</button>
            {session.signup_enabled&&<button disabled={authBusy||!username||!password}
              onClick={()=>void signIn('register')}>ثبت‌نام</button>}
          </div>{authError&&<p role="alert" className="auth-error">{authError}</p>}</>}
    </section>
    {session.authenticated&&<section className="obstacle-report">
      <h2><TrafficCone size={17}/> اصلاح اطلاعات موانع</h2>
      <p>برای گزارش مانع جدید «انتخاب محل» را بزنید و نقطه را روی نقشه مشخص کنید.
        برای اصلاح مانع موجود، علامت آن را روی نقشه انتخاب کنید.</p>
      <button className="text-button" onClick={()=>{reportMode.current=true;
        setReportAction('add');setReportObstacleId(null);setReportPoint(null);
        setReportMessage('روی نقشه محل مانع جدید را انتخاب کنید.');}}>انتخاب محل مانع جدید</button>
      <p>محل: {reportPoint?reportPoint.lat.toFixed(5)+'، '+reportPoint.lon.toFixed(5):'هنوز انتخاب نشده'}</p>
      {reportObstacleId&&<p>شناسه مانع انتخابی: {reportObstacleId}</p>}
      <label>درخواست
        <select value={reportAction} onChange={e=>setReportAction(e.target.value)}>
          <option value="add">افزودن</option>
          {reportObstacleId&&<option value="correct">اصلاح</option>}
          {reportObstacleId&&<option value="remove">حذف</option>}
        </select>
      </label>
      <label>نوع مانع
        <select value={reportKind} onChange={e=>setReportKind(e.target.value)}>
          {Object.entries(labels).map(([id,name])=><option key={id} value={id}>{name}</option>)}
        </select>
      </label>
      <label>نام خیابان<input value={reportRoad} onChange={e=>setReportRoad(e.target.value)} placeholder="نام خیابان در نقشه"/></label>
      <label>جهت اثر<select value={reportDirection} onChange={e=>setReportDirection(e.target.value)}>
        <option value="unknown">نامشخص</option><option value="both">هر دو جهت (نیازمند بازبینی)</option>
        <option value="forward">فقط یک جهت</option></select></label>
      <label>توضیحات<input value={reportNote} onChange={e=>setReportNote(e.target.value)} maxLength={1000}/></label>
      <button className="submit" disabled={!reportPoint||(reportAction!=='add'&&!reportObstacleId)}
        onClick={()=>void submitObstacle()}>ثبت گزارش برای بازبینی</button>
      {reportMessage&&<p role="status">{reportMessage}</p>}
    </section>}
    {session.staff&&<section className="moderation">
      <h2><ShieldCheck size={17}/> صف بازبینی مدیر</h2>
      <button className="text-button" onClick={()=>void refreshPending()}>دریافت گزارش‌های منتظر</button>
      {pendingReports.map(item=><div className="moderation-item" key={item.id}>
        <strong>#{item.id} · {labels[item.kind]||item.kind} · {item.action}</strong>
        <p>{item.road_name||'نام خیابان نامشخص'} · {item.direction}</p>
        <p>{item.note}</p>
        <div className="auth-actions"><button onClick={()=>void decidePending(item.id,'approve')}>تأیید</button>
          <button onClick={()=>void decidePending(item.id,'reject')}>رد</button></div>
      </div>)}
    </section>}
    <section><h2><MapPin size={17}/> مبدأ و مقصد</h2>
        <p>روی نقشه دو نقطه را انتخاب کنید، یا آدرس را جست‌وجو کنید.</p>
        <div className="geo-search"><label>جست‌وجوی مبدأ<input value={originText}
          onChange={e=>setOriginText(e.target.value)}
          onKeyDown={e=>{if(e.key==='Enter'){e.preventDefault();void geocode('origin');}}}
          placeholder="مثلاً میدان آزادی"/></label>
          <button disabled={geocodeBusy||originText.trim().length<2}
            onClick={()=>void geocode('origin')}>جست‌وجو</button></div>
        <div className="geo-search"><label>جست‌وجوی مقصد<input value={destText}
          onChange={e=>setDestText(e.target.value)}
          onKeyDown={e=>{if(e.key==='Enter'){e.preventDefault();void geocode('destination');}}}
          placeholder="مثلاً میدان تجریش"/></label>
          <button disabled={geocodeBusy||destText.trim().length<2}
            onClick={()=>void geocode('destination')}>جست‌وجو</button></div>
        {places.length>0&&<div className="place-results" role="listbox">
          {places.map((p,i)=><button key={i} onClick={()=>choosePlace(p,placeTarget)}>{p.label}</button>)}
        </div>}
        <div className="point">مبدأ: {origin?origin.lat.toFixed(4)+'، '+origin.lon.toFixed(4):'انتخاب نشده'}</div>
        <div className="point">مقصد: {destination?destination.lat.toFixed(4)+'، '+destination.lon.toFixed(4):'انتخاب نشده'}</div>
        <button className="text-button" onClick={reset}><RotateCcw size={14}/> شروع دوباره</button>
      </section>
      <section><h2><SlidersHorizontal size={17}/> سناریوی سفر</h2>
        <label>خودرو<input value="پراید ۱۳۱ - دنده دستی" readOnly/></label>
        <div className="inputs-two"><label>تعداد سرنشینان<input type="number" min="1" max="5"
          value={passengers} onChange={e=>setPassengers(Math.min(5,Math.max(1,+e.target.value||1)))}/></label>
        <label>وزن بار (کیلوگرم)<input type="number" min="0" max="150" value={cargo}
          onChange={e=>setCargo(Math.min(150,Math.max(0,+e.target.value||0)))}/></label></div>
        <label className="switch"><input type="checkbox" checked={ac} onChange={e=>setAc(e.target.checked)}/> کولر روشن است</label>
        <label className="switch"><input type="checkbox" checked={saveHistory}
          disabled={!session.authenticated}
          onChange={e=>setSaveHistory(e.target.checked)}/>
          ذخیره اختیاری مسیر برای اعتبارسنجی (فقط کاربران واردشده)</label>
        <label>احتمال فرضی قرمز بودن چراغ: {faNum(redProbability*100,0)}٪
          <input type="range" min="0" max="1" step=".1" value={redProbability}
            onChange={e=>setRedProbability(Number(e.target.value))}/>
        </label>
      </section>
      <button className="submit" disabled={!origin||!destination||busy} onClick={run}>
        <Fuel size={18}/>{busy?'در حال پردازش...':'محاسبه و مقایسه مسیرها'}</button>
      {error&&<div role="alert" className="error"><AlertTriangle size={18}/>{error}</div>}
      <section><h2><Fuel size={17}/> نتیجه مسیرها</h2>
        {routes.length?routes.map((r,i)=><button key={r.index} className={'route '+(selected===i?'active':'')}
          onClick={()=>setSelected(i)} aria-pressed={selected===i}>
          <span className="route-heading">مسیر {faNum(i+1,0)}: <strong>{faNum(r.estimated_l,2)} لیتر</strong>
          {i===routes.reduce((best,x,j,arr)=>x.estimated_l<arr[best].estimated_l?j:best,0)&&
            <span className="best">کم‌مصرف‌تر</span>}</span>
          <span>{faNum(r.distance_m/1000)} کیلومتر · حدود {faNum(r.modeled_duration_s/60,0)} دقیقه</span>
        </button>):<p className="empty">با انتخاب مبدأ و مقصد، مقایسه مسیرها اینجا نمایش داده می‌شود.</p>}
      </section>
      {active&&<section className="details">
        <h2><CheckCircle2 size={17}/> جزئیات تخمین</h2>
        <div className="stat-grid">
          <div><small>مصرف پایه</small><strong>{faNum(active.baseline_l,2)} L</strong></div>
          <div><small>بازه سناریوها</small><strong>{faNum(active.estimated_range_l[0],2)}–{faNum(active.estimated_range_l[1],2)} L</strong></div>
          <div><small>مصرف درجا</small><strong>{faNum(active.idle_l,3)} L</strong></div>
          <div><small>مصرف محرکه</small><strong>{faNum(active.propulsion_l,3)} L</strong></div>
        </div>
        <h3><TrafficCone size={16}/> شواهد موانع</h3>
        <p>نزدیک مسیر: {faNum(active.obstacle_summary.nearby,0)} مورد ·
          تأییدشده دستی: {faNum(active.obstacle_summary.reviewed_applied,0)} مورد ·
          تطبیق خودکار با نود مسیر: {faNum(active.obstacle_summary.topology_matched_osm_calming??0,0)} مورد</p>
        <p>توقف مدل‌شده: {faNum(active.obstacle_summary.stops,0)} ·
          کاهش سرعت: {faNum(active.obstacle_summary.slowdowns,0)} ·
          چراغ در سناریو: {faNum(active.obstacle_summary.signals_scenario,0)}</p>
        <h3>تغییرات ارتفاع</h3>
        <p>{active.terrain?'صعود '+faNum(active.terrain.ascent_m,0)+' متر؛ نزول '+faNum(active.terrain.descent_m,0)+' متر':'ارتفاع اندازه‌گیری نشده است.'}</p>
        <h3><AlertTriangle size={16}/> محدودیت‌های این محاسبه</h3>
        <ul className="warnings">{[...new Set(active.warnings)].slice(0,9).map(w=>
          <li key={w}>{warnings[w]||w.replaceAll('_',' ')}</li>)}</ul>
        <small>نسخه مدل: {active.model_version}</small>
      </section>}
      {session.authenticated&&active?.prediction_id&&<section className="observation">
        <h2><Fuel size={17}/> ثبت مصرف واقعی همین مسیر</h2>
        <p>تنها در صورت اندازه‌گیری واقعی بنزین، داده را ثبت کنید. مقدار تخمینی را به‌عنوان مقدار واقعی وارد نکنید.</p>
        <div className="inputs-two">
          <label>مسافت واقعی (متر)<input type="number" min="100" max="100000" step="1"
            value={observedDistance} onChange={e=>setObservedDistance(e.target.value)}/></label>
          <label>بنزین اندازه‌گیری‌شده (لیتر)<input type="number" min=".001" max="30" step=".001"
            value={observedFuel} onChange={e=>setObservedFuel(e.target.value)}/></label>
        </div>
        <label>روش اندازه‌گیری<select value={observationMethod}
          onChange={e=>setObservationMethod(e.target.value)}>
          <option value="obd">OBD / ECU</option><option value="full_tank">باک پُر (کم‌دقت برای سفر کوتاه)</option>
          <option value="other">روش دیگر</option></select></label>
        <label className="switch"><input type="checkbox" checked={consent}
          onChange={e=>setConsent(e.target.checked)}/>
          با ذخیره داده این سفر برای ارزیابی مدل موافقم.</label>
        <button className="submit" disabled={!consent} onClick={()=>void submitObservation()}>ثبت اندازه‌گیری</button>
        {observationMessage&&<p role="status">{observationMessage}</p>}
      </section>}
      <p className="disclaimer"><ShieldCheck size={15}/> اعداد تخمینی‌اند و هنوز با داده مصرف واقعی پراید اعتبارسنجی نشده‌اند. مسیرها از OSRM دریافت می‌شوند و پوشش کامل موانع تضمین نمی‌شود.</p>
    </aside>
    <main><div ref={mapNode} className="map" aria-label="نقشه تعاملی تهران"/>
      <div className="map-legend"><span><i className="dot" style={{background:'#1b866c'}}/>مانع تأییدشده</span>
        <span><i className="dot" style={{background:'#ee973a'}}/>مانع نقشه</span>
        <span className="legend-count">{faNum(obstacles.length,0)} مورد در محدوده نمایشی</span>
        {obstacleWarning&&<small>{obstacleWarning}</small>}</div>
    </main>
  </div>;
}
