import { useEffect, useRef, useState } from 'react';
import maplibregl, { type Map as MapType, type GeoJSONSource } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { CarFront, Fuel, MapPin, AlertTriangle } from 'lucide-react';

type Point={lat:number;lon:number};
type Route={index:number;distance_m:number;osrm_duration_s:number;estimated_l:number;baseline_l:number;warnings:string[];geometry:{type:'LineString';coordinates:number[][]}};
const API=import.meta.env.VITE_API_BASE_URL || '';
const TEHRAN: [number,number]=[51.3890,35.6892];
export default function App(){
  const mapNode=useRef<HTMLDivElement>(null),map=useRef<MapType|null>(null);
  const [origin,setOrigin]=useState<Point|null>(null),[destination,setDestination]=useState<Point|null>(null);
  const [routes,setRoutes]=useState<Route[]>([]),[selected,setSelected]=useState(0);
  const [passengers,setPassengers]=useState(1),[ac,setAc]=useState(false),[cargo,setCargo]=useState(0);
  const [error,setError]=useState(''),[busy,setBusy]=useState(false);
  const points=useRef<{origin:Point|null;destination:Point|null}>({origin:null,destination:null});
  useEffect(()=>{if(!mapNode.current)return;
    const m=new maplibregl.Map({container:mapNode.current,style:import.meta.env.VITE_MAP_STYLE_URL||'https://demotiles.maplibre.org/style.json',center:TEHRAN,zoom:11});
    m.addControl(new maplibregl.NavigationControl(),'top-left');
    m.on('click',(ev)=>{const p={lat:ev.lngLat.lat,lon:ev.lngLat.lng};
      if(p.lat<35.45||p.lat>35.95||p.lon<51.05||p.lon>51.75){setError('لطفاً نقطه‌ای در محدوده تهران انتخاب کنید.');return;}
      setError('');setRoutes([]);
      const next=points.current.origin&&!points.current.destination?'destination':'origin';
      if(next==='origin'){points.current={origin:p,destination:null};setOrigin(p);setDestination(null);}else{points.current.destination=p;setDestination(p);}
    });
    map.current=m;return()=>{m.remove();map.current=null;};
  },[]);
  useEffect(()=>{const m=map.current;if(!m)return;const markers:maplibregl.Marker[]=[];
    for(const [p,color] of [[origin,'#1b8a60'],[destination,'#dd6651']] as const){if(p)markers.push(new maplibregl.Marker({color}).setLngLat([p.lon,p.lat]).addTo(m));}
    return()=>markers.forEach(x=>x.remove());
  },[origin,destination]);
  useEffect(()=>{const m=map.current;if(!m)return;
    const update=()=>{if(!m.isStyleLoaded())return;
      const id='rahsu-route'; const src=m.getSource(id) as GeoJSONSource|undefined;
      const route=routes[selected];const feature:{type:'Feature';geometry:{type:'LineString';coordinates:number[][]};properties:Record<string,never>}={type:'Feature',geometry:route?.geometry||{type:'LineString',coordinates:[]},properties:{}};
      if(src)src.setData(feature);else{m.addSource(id,{type:'geojson',data:feature});m.addLayer({id,type:'line',source:id,paint:{'line-color':'#2563eb','line-width':6,'line-opacity':.9}});}
      if(route)m.fitBounds(route.geometry.coordinates.reduce((bounds,c)=>bounds.extend(c as [number,number]),new maplibregl.LngLatBounds(route.geometry.coordinates[0] as [number,number],route.geometry.coordinates[0] as [number,number])),{padding:55,maxZoom:15});
    };
    if(m.isStyleLoaded())update();else m.once('load',update);
  },[routes,selected]);
  const run=async()=>{if(!origin||!destination)return;setBusy(true);setError('');setRoutes([]);
    try{const response=await fetch(API+'/api/v1/estimates/',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({origin,destination,passengers,cargo_kg:cargo,ac_on:ac})});
      const payload=await response.json();if(!response.ok)throw new Error(payload.error==='routing_provider_unavailable'?'موتور مسیریابی تهران در دسترس نیست. داده OSRM باید بارگذاری شود.':JSON.stringify(payload));
      setRoutes(payload.routes||[]);setSelected(0);
    }catch(e){setError(e instanceof Error?e.message:'خطا در ارتباط با سرور');}finally{setBusy(false);}
  };
  return <div className="layout"><aside className="sidebar"><header><span className="brand"><CarFront size={24}/> راه‌سو</span><small>پیش‌بینی پژوهشی مصرف بنزین پراید | تهران</small></header>
    <section><h2><MapPin size={18}/> تعیین مسیر</h2><p>روی نقشه ابتدا مبدأ و سپس مقصد را انتخاب کنید.</p>
    <div className="point">مبدأ: {origin?`${origin.lat.toFixed(4)}، ${origin.lon.toFixed(4)}`:'انتخاب نشده'}</div>
    <div className="point">مقصد: {destination?`${destination.lat.toFixed(4)}، ${destination.lon.toFixed(4)}`:'انتخاب نشده'}</div>
    <button className="text-button" onClick={()=>{points.current={origin:null,destination:null};setOrigin(null);setDestination(null);setRoutes([]);}}>پاک کردن انتخاب‌ها</button>
    </section><section><h2><CarFront size={18}/> مشخصات خودرو</h2><label>خودرو<input value="پراید ۱۳۱ دنده‌ای" readOnly/></label>
    <label>تعداد سرنشینان (شامل راننده)<input type="number" min="1" max="5" value={passengers} onChange={e=>setPassengers(Math.min(5,Math.max(1,+e.target.value||1)))}/></label>
    <label>وزن بار (کیلوگرم)<input type="number" min="0" max="150" value={cargo} onChange={e=>setCargo(Math.min(150,Math.max(0,+e.target.value||0)))}/></label>
    <label className="switch"><input type="checkbox" checked={ac} onChange={e=>setAc(e.target.checked)}/> کولر روشن است</label></section>
    <button className="submit" disabled={!origin||!destination||busy} onClick={run}><Fuel size={18}/>{busy?'در حال محاسبه...':'تخمین مصرف مسیر'}</button>
    {error&&<div className="error" role="alert"><AlertTriangle size={17}/>{error}</div>}
    <section><h2>نتیجه تخمین</h2>{routes.length?routes.map((r,i)=><button className={'route '+(selected===i?'active':'')} key={i} onClick={()=>setSelected(i)}><strong>مسیر {i+1}: {r.estimated_l.toFixed(2)} لیتر</strong><span>{(r.distance_m/1000).toFixed(1)} کیلومتر · مصرف پایه {r.baseline_l.toFixed(2)} لیتر</span></button>):<p>برای مشاهده مصرف، مبدأ و مقصد را تعیین کنید.</p>}</section>
    <p className="disclaimer">این اعداد با مدل کالیبره‌نشده تولید می‌شوند. ترافیک زنده، شیب و موانع هنوز در محاسبه اعمال نشده‌اند.</p>
    </aside><main><div ref={mapNode} className="map" aria-label="نقشه تعاملی تهران" /></main></div>;
}
