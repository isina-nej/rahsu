import { useEffect, useRef, useState } from 'react';
import maplibregl, { type Map as MapType, type GeoJSONSource } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { AlertTriangle, CarFront, CheckCircle2, Fuel, MapPin, RotateCcw, ShieldCheck, SlidersHorizontal, TrafficCone } from 'lucide-react';

type Point = {lat:number;lon:number};
type Obstacle = {id:number;kind:string;lon:number;lat:number;source:string;verified:boolean;road_name:string};
type Route = {
  index:number; distance_m:number; osrm_duration_s:number; modeled_duration_s:number;
  estimated_l:number;estimated_range_l:number[];baseline_l:number;
  idle_l:number;propulsion_l:number;warnings:string[];
  obstacle_summary:{nearby:number;reviewed_applied:number;signals_scenario:number;stops:number;slowdowns:number};
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
  unreviewed_osm_not_applied:'موانع OSM بدون تأیید مدیر وارد محاسبه نشده‌اند.',
  manual_obstacle_matching_is_conservative:'تطبیق موانع با مسیر محافظه‌کارانه است.',
  idealized_engine_and_drive_cycle:'مدل موتور و الگوی حرکت ساده‌سازی شده‌اند.',
  dem_resolution_limited:'داده ارتفاع محدودیت تفکیک مکانی دارد.'
};
const faNum=(num:number,digits=1)=>num.toLocaleString('fa-IR',{maximumFractionDigits:digits,minimumFractionDigits:digits});
const typeColor=(o:Obstacle)=>o.verified?'#1b866c':'#ee973a';
const EMPTY={type:'FeatureCollection' as const,features:[]};
const within=(p:Point)=>p.lat>=LIMIT.minLat&&p.lat<=LIMIT.maxLat&&p.lon>=LIMIT.minLon&&p.lon<=LIMIT.maxLon;

export default function App(){
  const mapNode=useRef<HTMLDivElement>(null);
  const map=useRef<MapType|null>(null);
  const points=useRef<{origin:Point|null;destination:Point|null}>({origin:null,destination:null});
  const [origin,setOrigin]=useState<Point|null>(null),[destination,setDestination]=useState<Point|null>(null);
  const [routes,setRoutes]=useState<Route[]>([]),[selected,setSelected]=useState(0);
  const [obstacles,setObstacles]=useState<Obstacle[]>([]);
  const [obstacleWarning,setObstacleWarning]=useState('');
  const [passengers,setPassengers]=useState(1),[ac,setAc]=useState(false),[cargo,setCargo]=useState(0);
  const [redProbability,setRedProbability]=useState(0.5);
  const [error,setError]=useState(''),[busy,setBusy]=useState(false);

  useEffect(()=>{
    if(!mapNode.current)return;
    const m=new maplibregl.Map({container:mapNode.current,
      style:import.meta.env.VITE_MAP_STYLE_URL||'https://demotiles.maplibre.org/style.json',
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
      setError('');setRoutes([]);
      const next=points.current.origin&&!points.current.destination?'destination':'origin';
      if(next==='origin'){
        points.current={origin:p,destination:null};setOrigin(p);setDestination(null);
      }else{points.current.destination=p;setDestination(p);}
    });
    m.on('click','obstacles',(ev)=>{
      const feature=ev.features?.[0];if(!feature||feature.geometry.type!=='Point')return;
      const p=feature.properties||{};
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

  const reset=()=>{points.current={origin:null,destination:null};
    setOrigin(null);setDestination(null);setRoutes([]);setError('');};
  const run=async()=>{
    if(!origin||!destination)return;setBusy(true);setError('');setRoutes([]);
    try{
      const response=await fetch(API+'/api/v1/estimates/',{
        method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({origin,destination,passengers,cargo_kg:cargo,ac_on:ac,
          signal_red_probability:redProbability})
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
      <section><h2><MapPin size={17}/> مبدأ و مقصد</h2>
        <p>روی نقشه دو نقطه را به‌ترتیب انتخاب کنید. مختصات فقط برای محاسبه ارسال می‌شود.</p>
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
          اثرگذار پس از تأیید: {faNum(active.obstacle_summary.reviewed_applied,0)} مورد</p>
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
