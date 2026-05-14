import React, { useState, useEffect, useMemo } from "react";
import {
  Printer, Edit3, Target, Home as HomeIcon, ShieldAlert, Bot, Sparkles, X,
  CheckCircle2, Briefcase, Landmark, Activity, GraduationCap, Loader2, Clock,
  UserCog, Wand2, ArrowDownCircle, Scale, FileCheck, RefreshCw, User,
  TrendingUp, TrendingDown, BarChart2, ArrowRight, Minus, IndianRupee, Zap,
} from "lucide-react";
import { TaxService } from "@shared/services/taxService";
import { AIService } from "@shared/services/aiService";
import { formatIndianCompact } from "@shared/utils/helpers";
import { TABS } from "@shared/config/constants";
import { apiFetch } from "../api";
import { GenericPageSkeleton } from "../components/ui/Skeletons";

// ─── Helpers ──────────────────────────────────────────────────────────────────

const fmt = (n) => "₹" + Number(n || 0).toLocaleString("en-IN");
const fmtC = (n) => formatIndianCompact(n || 0);

function calcNewTax(income) {
  const slabs = [
    [400000,0],[800000,.05],[1200000,.10],[1600000,.15],
    [2000000,.20],[2400000,.25],[Infinity,.30],
  ];
  let tax=0, prev=0;
  for(const [upto,rate] of slabs){
    if(income<=prev)break;
    tax+=(Math.min(income,upto)-prev)*rate;
    prev=upto;
  }
  if(income<=1200000)tax=0;
  return Math.round(tax*1.04);
}

function calcOldTax(income) {
  const slabs=[[250000,0],[500000,.05],[1000000,.20],[Infinity,.30]];
  let tax=0,prev=0;
  for(const [upto,rate] of slabs){
    if(income<=prev)break;
    tax+=(Math.min(income,upto)-prev)*rate;
    prev=upto;
  }
  if(income<=500000)tax=0;
  return Math.round(tax*1.04);
}

// ─── Shared UI ────────────────────────────────────────────────────────────────

const DeductionBar = ({ label, used, limit, color="bg-blue-500" }) => {
  const pct = Math.min(100,(used/limit)*100);
  return (
    <div className="mb-4">
      <div className="flex justify-between text-xs mb-1.5">
        <span className="text-slate-300 font-medium">{label}</span>
        <span className={`font-semibold ${pct>=100?"text-emerald-400":"text-slate-400"}`}>
          {fmtC(used)} / {fmtC(limit)} {pct>=100&&"✓"}
        </span>
      </div>
      <div className="h-2 w-full bg-black/40 rounded-full overflow-hidden border border-white/5">
        <div className={`h-full ${color} rounded-full transition-all duration-700`} style={{width:`${pct}%`}}/>
      </div>
    </div>
  );
};

const TaxActionCard = ({ action, section, savings, deadline }) => (
  <div className="p-4 rounded-2xl bg-emerald-900/20 border border-emerald-500/20 hover:border-emerald-500/40 transition-all">
    <div className="flex justify-between items-start mb-2">
      <span className="bg-emerald-500/15 text-emerald-300 text-[10px] font-bold px-2 py-0.5 rounded-md border border-emerald-500/20 uppercase">{section}</span>
      <div className="flex items-center gap-1 text-[10px] text-slate-400"><Clock className="w-3 h-3"/>{deadline}</div>
    </div>
    <h4 className="font-bold text-white text-sm mb-1">{action}</h4>
    <p className="text-xs text-slate-400">Potential savings: <span className="text-emerald-300 font-bold">{savings}</span></p>
  </div>
);

// ─── YoY SVG Chart ────────────────────────────────────────────────────────────

function YoYChart({ data }) {
  if(!data||data.length<2)return null;
  const W=100,H=60,PAD=8;
  const maxVal=Math.max(...data.map(d=>Math.max(d.income,d.tax)))*1.1||1;
  const sx=(i)=>PAD+(i/(data.length-1))*(W-PAD*2);
  const sy=(v)=>H-PAD-(v/maxVal)*(H-PAD*2);
  const ip=data.map((d,i)=>`${i===0?"M":"L"}${sx(i)},${sy(d.income)}`).join(" ");
  const tp=data.map((d,i)=>`${i===0?"M":"L"}${sx(i)},${sy(d.tax)}`).join(" ");
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-24 overflow-visible">
      <path d={ip} fill="none" stroke="#22d3ee" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
      <path d={tp} fill="none" stroke="#f87171" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
      {data.map((d,i)=>(
        <g key={i}>
          <circle cx={sx(i)} cy={sy(d.income)} r="2" fill="#22d3ee"/>
          <circle cx={sx(i)} cy={sy(d.tax)} r="2" fill="#f87171"/>
          <text x={sx(i)} y={H-1} textAnchor="middle" fontSize="4" fill="#64748b">{d.fy}</text>
        </g>
      ))}
    </svg>
  );
}

// ─── YoY Section ─────────────────────────────────────────────────────────────

function YoYSection({ transactions }) {
  const yearData = useMemo(()=>{
    if(!Array.isArray(transactions)||transactions.length===0)return [];
    const byYear={};
    transactions.forEach(t=>{
      if(!t?.date)return;
      const d=new Date(t.date);
      if(isNaN(d))return;
      const m=d.getMonth();
      const fyStart=m>=3?d.getFullYear():d.getFullYear()-1;
      const fy=`${String(fyStart).slice(-2)}-${String(fyStart+1).slice(-2)}`;
      if(!byYear[fy])byYear[fy]={fy,income:0,expenses:0,salary:0,investments:0};
      const amt=parseFloat(t.amount)||0;
      const desc=(t.description||"").toLowerCase();
      const cat=(t.category||"").toLowerCase();
      if(t.type==="income"){
        byYear[fy].income+=amt;
        if(desc.includes("salary")||cat==="salary")byYear[fy].salary+=amt;
      } else {
        byYear[fy].expenses+=amt;
        if(desc.includes("ppf")||desc.includes("elss")||desc.includes("nps")||cat==="investment")
          byYear[fy].investments+=amt;
      }
    });
    return Object.values(byYear)
      .sort((a,b)=>a.fy.localeCompare(b.fy))
      .map(y=>({
        ...y,
        tax:calcNewTax(Math.max(0,y.salary-75000)),
        effectiveRate:y.salary>0?((calcNewTax(Math.max(0,y.salary-75000))/y.salary)*100).toFixed(1):"0.0",
      }));
  },[transactions]);

  if(yearData.length<2){
    return (
      <div className="rounded-2xl border border-white/8 bg-white/[0.02] p-8 text-center">
        <BarChart2 className="w-8 h-8 text-slate-600 mx-auto mb-3"/>
        <p className="text-sm text-slate-400">Need 2+ years of transactions for year-over-year analysis.</p>
        <p className="text-xs text-slate-600 mt-1">Keep tracking your income and expenses to unlock this view.</p>
      </div>
    );
  }

  const latest=yearData[yearData.length-1];
  const prev=yearData[yearData.length-2];
  const incomeChg=prev.income>0?((latest.income-prev.income)/prev.income)*100:0;
  const taxChg=prev.tax>0?((latest.tax-prev.tax)/prev.tax)*100:0;
  const invChg=prev.investments>0?((latest.investments-prev.investments)/prev.investments)*100:0;

  const Trend=({v,good})=>{
    if(v===0)return <Minus className="w-3 h-3 text-slate-500"/>;
    const up=v>0;
    const ok=good?up:!up;
    return up
      ?<TrendingUp className={`w-3 h-3 ${ok?"text-emerald-400":"text-rose-400"}`}/>
      :<TrendingDown className={`w-3 h-3 ${ok?"text-emerald-400":"text-rose-400"}`}/>;
  };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-3">
        {[
          {label:"Income",value:fmtC(latest.income),chg:incomeChg,good:true,icon:IndianRupee,col:"text-cyan-400",bg:"bg-cyan-500/8 border-cyan-500/15"},
          {label:"Est. Tax",value:fmtC(latest.tax),chg:taxChg,good:false,icon:Target,col:"text-rose-400",bg:"bg-rose-500/8 border-rose-500/15"},
          {label:"Investments",value:fmtC(latest.investments),chg:invChg,good:true,icon:TrendingUp,col:"text-emerald-400",bg:"bg-emerald-500/8 border-emerald-500/15"},
        ].map(s=>{
          const up=s.chg>0;
          const ok=s.good?up:!up;
          return (
            <div key={s.label} className={`rounded-2xl border p-4 ${s.bg}`}>
              <div className="flex items-center justify-between mb-2">
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">{s.label}</p>
                <s.icon className={`w-3.5 h-3.5 ${s.col} opacity-60`}/>
              </div>
              <p className={`text-xl font-black ${s.col} mb-1`}>{s.value}</p>
              <div className="flex items-center gap-1">
                <Trend v={s.chg} good={s.good}/>
                <span className={`text-[10px] font-semibold ${s.chg===0?"text-slate-400":ok?"text-emerald-400":"text-rose-400"}`}>
                  {s.chg===0?"No change":`${up?"+":""}${s.chg.toFixed(1)}% vs FY ${prev.fy}`}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      <div className="rounded-2xl border border-white/8 bg-white/[0.02] p-5">
        <div className="flex items-center justify-between mb-4">
          <p className="text-xs font-bold text-white">Income vs Tax Trend</p>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1.5"><div className="w-3 h-0.5 bg-cyan-400 rounded"/><span className="text-[10px] text-slate-400">Income</span></div>
            <div className="flex items-center gap-1.5"><div className="w-3 h-0.5 bg-rose-400 rounded"/><span className="text-[10px] text-slate-400">Est. Tax</span></div>
          </div>
        </div>
        <YoYChart data={yearData}/>
      </div>

      <div className="rounded-2xl border border-white/8 bg-white/[0.02] overflow-hidden">
        <div className="grid grid-cols-4 px-4 py-2.5 border-b border-white/5 text-[10px] font-bold text-slate-500 uppercase tracking-wider">
          <span>FY</span><span className="text-right">Income</span><span className="text-right">Est. Tax</span><span className="text-right">Eff. Rate</span>
        </div>
        {yearData.map((y,i)=>{
          const isLatest=i===yearData.length-1;
          return (
            <div key={y.fy} className={`grid grid-cols-4 px-4 py-3 text-sm border-b border-white/5 last:border-0 ${isLatest?"bg-white/[0.03]":""}`}>
              <span className={`font-semibold ${isLatest?"text-cyan-400":"text-slate-300"}`}>
                FY {y.fy}{isLatest&&<span className="text-[9px] bg-cyan-500/15 text-cyan-400 px-1.5 py-0.5 rounded-full ml-1.5">Now</span>}
              </span>
              <span className="text-right text-slate-200 font-medium">{fmtC(y.income)}</span>
              <span className="text-right text-rose-300 font-medium">{fmtC(y.tax)}</span>
              <span className="text-right text-slate-400 text-xs">{y.effectiveRate}%</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Regime Comparison ────────────────────────────────────────────────────────

function RegimeComparison({ income, deductions }) {
  const stdDed=75000;
  const newTax=calcNewTax(Math.max(0,income-stdDed));
  const oldTax=calcOldTax(Math.max(0,income-stdDed-deductions));
  const diff=Math.abs(newTax-oldTax);
  const newWins=newTax<=oldTax;
  const maxTax=Math.max(newTax,oldTax)||1;
  const breakEven=income>0?Math.max(0,(calcOldTax(income-stdDed)-calcNewTax(income-stdDed))/0.30):0;

  return (
    <div className="space-y-5">
      <div className={`rounded-2xl border p-5 ${newWins?"border-cyan-500/30 bg-cyan-500/5":"border-amber-500/30 bg-amber-500/5"}`}>
        <div className="flex items-start justify-between mb-5">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1">Recommended Regime</p>
            <div className="flex items-center gap-2">
              <span className={`text-2xl font-black ${newWins?"text-cyan-400":"text-amber-400"}`}>
                {newWins?"New Regime":"Old Regime"}
              </span>
              <span className={`text-xs font-bold px-2 py-0.5 rounded-full border ${newWins?"bg-cyan-500/15 text-cyan-300 border-cyan-500/20":"bg-amber-500/15 text-amber-300 border-amber-500/20"}`}>
                Saves {fmtC(diff)}
              </span>
            </div>
          </div>
          <Zap className={`w-8 h-8 opacity-30 ${newWins?"text-cyan-400":"text-amber-400"}`}/>
        </div>

        <div className="grid grid-cols-2 gap-3">
          {[
            {label:"New Regime",tax:newTax,wins:newWins},
            {label:"Old Regime",tax:oldTax,wins:!newWins},
          ].map(r=>(
            <div key={r.label} className={`rounded-xl p-4 border ${r.wins?"border-emerald-500/30 bg-emerald-500/8":"border-white/8 bg-white/[0.02]"}`}>
              <p className="text-[10px] text-slate-400 mb-1 font-semibold">{r.label} Tax</p>
              <p className={`text-xl font-black ${r.wins?"text-emerald-400":"text-slate-300"}`}>{fmtC(r.tax)}</p>
              <div className="mt-2.5 h-1.5 rounded-full bg-black/30 overflow-hidden">
                <div className={`h-full rounded-full transition-all duration-700 ${r.wins?"bg-emerald-500":"bg-slate-500"}`}
                  style={{width:`${(r.tax/maxTax)*100}%`}}/>
              </div>
            </div>
          ))}
        </div>

        {income>0&&(
          <p className="text-xs text-slate-400 mt-4 leading-relaxed">
            {deductions>0
              ?<>Your deductions of <span className="text-white font-semibold">{fmtC(deductions)}</span> make {newWins?"New Regime still optimal.":"Old Regime beneficial."} </>
              :"No deductions entered — "}
            Break-even: ~<span className="text-white font-semibold">{fmtC(breakEven)}</span> in deductions needed to switch.
          </p>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4">
        {[
          {title:"New Regime Slabs",slabs:[["0%","Up to ₹4L"],["5%","₹4L–8L"],["10%","₹8L–12L"],["15%","₹12L–16L"],["20%","₹16L–20L"],["25%","₹20L–24L"],["30%","Above ₹24L"]],colors:["bg-emerald-500","bg-teal-500","bg-cyan-500","bg-sky-500","bg-blue-500","bg-indigo-500","bg-violet-500"],note:"Rebate u/s 87A: Zero tax up to ₹12L income",wins:newWins},
          {title:"Old Regime Slabs",slabs:[["0%","Up to ₹2.5L"],["5%","₹2.5L–5L"],["20%","₹5L–10L"],["30%","Above ₹10L"]],colors:["bg-emerald-500","bg-amber-500","bg-orange-500","bg-rose-500"],note:"Rebate u/s 87A: Zero tax up to ₹5L income",wins:!newWins},
        ].map(regime=>(
          <div key={regime.title} className="rounded-2xl border border-white/8 bg-white/[0.02] p-4">
            <div className="flex items-center justify-between mb-3">
              <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">{regime.title}</p>
              {regime.wins&&<span className="text-[9px] font-bold text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded-full border border-emerald-500/20">BETTER FOR YOU</span>}
            </div>
            <div className="space-y-2 mb-3">
              {regime.slabs.map(([rate,range],i)=>(
                <div key={rate+range} className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full shrink-0 ${regime.colors[i]}`}/>
                  <span className="text-[10px] font-bold text-slate-300 w-8 shrink-0">{rate}</span>
                  <span className="text-[10px] text-slate-500">{range}</span>
                </div>
              ))}
            </div>
            <div className="pt-3 border-t border-white/8">
              <p className="text-[10px] text-slate-500 mb-1">{regime.note}</p>
              <p className="text-[10px] text-slate-400">Your est. tax (incl. cess)</p>
              <p className={`text-base font-black ${regime.wins?"text-emerald-400":"text-slate-300"}`}>
                {regime.wins?fmtC(newWins?newTax:oldTax):fmtC(newWins?oldTax:newTax)}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Profile Wizard ───────────────────────────────────────────────────────────

const ProfileWizard = ({ isOpen, onClose, initialData, detectedValues, onSave }) => {
  const [local, setLocal] = useState(initialData);
  useEffect(()=>{ if(initialData)setLocal(initialData); },[initialData]);
  if(!isOpen)return null;

  const fields=[
    {label:"Annual Rent Paid",key:"annualRent",icon:HomeIcon,detected:detectedValues.rent},
    {label:"Annual EPF",key:"annualEPF",icon:Briefcase,detected:detectedValues.epf},
    {label:"NPS Contribution",key:"npsContribution",icon:Landmark,detected:detectedValues.nps},
    {label:"Health Ins. (Self)",key:"healthInsuranceSelf",icon:Activity,detected:detectedValues.health},
    {label:"Health Ins. (Parents)",key:"healthInsuranceParents",icon:Activity,detected:0},
    {label:"Home Loan Interest",key:"homeLoanInterest",icon:HomeIcon,detected:0},
    {label:"Edu Loan Interest",key:"educationLoanInterest",icon:GraduationCap,detected:0},
    {label:"Your Age",key:"age",icon:User,detected:30},
  ];
  const toggles=[
    {label:"I have Business Income",key:"isBusiness",sub:"Apart from salary"},
    {label:"I live in a Metro City",key:"isMetro",sub:"HRA is higher for metro"},
    {label:"Parents are Senior Citizens",key:"parentsAreSenior",sub:"80D limit → ₹50k"},
    {label:"I am an NRI",key:"isNRI",sub:"Non-Resident Indian"},
    {label:"I have Foreign Assets",key:"foreignAssets",sub:"Schedule FA required"},
  ];

  return (
    <div className="fixed inset-0 bg-black/80 z-[60] flex items-center justify-center p-4 backdrop-blur-sm">
      <div className="bg-[#0f0c29] w-full max-w-xl p-6 rounded-[2rem] border border-white/10 shadow-2xl relative">
        <button onClick={onClose} className="absolute top-4 right-4 p-2 bg-white/5 hover:bg-white/10 rounded-full text-slate-400 hover:text-white transition-colors">
          <X className="w-4 h-4"/>
        </button>
        <h3 className="text-xl font-bold text-white mb-6">Update Tax Profile</h3>
        <div className="space-y-5 max-h-[72vh] overflow-y-auto pr-2">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {toggles.map(t=>(
              <div key={t.key} className="flex items-center gap-3 p-3.5 bg-white/5 rounded-xl border border-white/10 cursor-pointer hover:bg-white/8 transition-colors"
                onClick={()=>setLocal({...local,[t.key]:!local[t.key]})}>
                <div className={`shrink-0 w-5 h-5 rounded-md border flex items-center justify-center ${local[t.key]?"bg-blue-500 border-blue-500":"border-slate-500"}`}>
                  {local[t.key]&&<CheckCircle2 className="w-3.5 h-3.5 text-white"/>}
                </div>
                <div>
                  <p className="text-xs font-bold text-white">{t.label}</p>
                  <p className="text-[9px] text-slate-400">{t.sub}</p>
                </div>
              </div>
            ))}
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {fields.map(f=>(
              <div key={f.key} className="space-y-1.5">
                <div className="flex justify-between items-center">
                  <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1">
                    <f.icon className="w-3 h-3"/>{f.label}
                  </label>
                  {f.detected>0&&(
                    <button type="button" onClick={()=>setLocal({...local,[f.key]:Math.round(Number(f.detected)||0)})}
                      className="text-[9px] font-bold text-cyan-300 bg-cyan-500/10 px-2 py-0.5 rounded flex items-center gap-1 hover:bg-cyan-500/20 transition-colors">
                      <ArrowDownCircle className="w-3 h-3"/>₹{formatIndianCompact(f.detected)}
                    </button>
                  )}
                </div>
                <input type="number"
                  value={!local[f.key]||Number(local[f.key])===0?"":local[f.key]}
                  onChange={e=>{const v=e.target.value===""?0:parseFloat(e.target.value);setLocal({...local,[f.key]:isNaN(v)?0:Math.max(0,v)});}}
                  className="w-full px-3 py-2.5 bg-black/40 border border-white/10 rounded-xl text-white text-sm outline-none focus:border-blue-500/50 transition-colors placeholder:text-slate-600"
                  placeholder={f.detected>0?`Detected: ${f.detected}`:"Enter amount..."}/>
              </div>
            ))}
          </div>
        </div>
        <div className="pt-5 mt-2 border-t border-white/5">
          <button onClick={()=>{onSave(local);onClose();}}
            className="w-full bg-blue-600 hover:bg-blue-500 text-white py-3.5 rounded-xl font-bold transition-all">
            Save Profile
          </button>
        </div>
      </div>
    </div>
  );
};

// ─── Tab config ───────────────────────────────────────────────────────────────

const AUDIT_TABS=[
  {id:"overview",label:"Overview",icon:FileCheck},
  {id:"yoy",label:"YoY Progress",icon:TrendingUp},
  {id:"regime",label:"Regime Comparison",icon:Scale},
  {id:"ai",label:"AI Consultant",icon:Bot},
];

// ─── Main AuditPage ───────────────────────────────────────────────────────────

const AuditPage = ({
  transactions, wealthItems, taxProfile, onUpdateProfile,
  showToast, settings, setActiveTab, user, apiBaseUrl, isLoading,
}) => {
  if(isLoading)return <GenericPageSkeleton/>;

  const [tab, setTab]=useState("overview");
  const [adviceCards, setAdviceCards]=useState([]);
  const [aiLoading, setAiLoading]=useState(false);
  const [showWizard, setShowWizard]=useState(false);
  const [isRateLimited, setIsRateLimited]=useState(false);

  useEffect(()=>{
    const c=localStorage.getItem("tax_audit_advice");
    if(c){try{setAdviceCards(JSON.parse(c));}catch{}}
  },[]);

  const data=useMemo(()=>{
    const r=TaxService.calculate(transactions,taxProfile,wealthItems,settings);
    const cheaper=r.taxNew<=r.taxOld;
    return{...r,isNewCheaper:cheaper,recommendedTaxable:cheaper?r.taxableNew:r.taxableOld,recommendedTax:cheaper?r.taxNew:r.taxOld};
  },[transactions,taxProfile,wealthItems,settings]);

  const detectedValues=useMemo(()=>{
    const r={rent:0,epf:0,health:0,nps:0};
    transactions.forEach(t=>{
      const desc=(t.description||"").toLowerCase();
      const val=parseFloat(t.amount);
      if(t.type==="expense"){
        if(desc.includes("rent")&&val>1000)r.rent+=val;
        if(desc.includes("ppf")||desc.includes("lic")||desc.includes("elss"))r.epf+=val;
        if((desc.includes("health")||desc.includes("mediclaim"))&&!desc.includes("lic"))r.health+=val;
        if(desc.includes("nps"))r.nps+=val;
      }
    });
    return r;
  },[transactions]);

  const userPersona=useMemo(()=>{
    const tags=[];
    if(taxProfile.isBusiness)tags.push("Freelancer");else tags.push("Salaried");
    if(data.sources?.total>1500000)tags.push("High Net Worth");
    return tags;
  },[taxProfile,data]);

  const integrityScore=useMemo(()=>{
    if(transactions.length===0)return 100;
    const v=transactions.filter(t=>t.verificationStatus==="verified"||t.confidence>0).length;
    return Math.round((v/transactions.length)*100);
  },[transactions]);

  const integrityColor=integrityScore<50?"text-rose-400":integrityScore<80?"text-amber-400":"text-emerald-400";
  const integrityLabel=integrityScore<50?"High Audit Risk":integrityScore<80?"Verify Data":"Audit Ready";

  const totalDeductions=(taxProfile.annualEPF||0)+(taxProfile.npsContribution||0)+
    (taxProfile.healthInsuranceSelf||0)+(taxProfile.healthInsuranceParents||0)+
    (taxProfile.homeLoanInterest||0)+(taxProfile.educationLoanInterest||0);

  const getAdvice=async()=>{
    if(aiLoading||isRateLimited)return;
    setAiLoading(true);
    try{
      const ctx=JSON.stringify({persona:userPersona.join(", "),regime:data.isNewCheaper?"New":"Old",income:{total:data.sources?.total,salary:data.heads?.salary},taxLiability:data.recommendedTax,unused80C:(data.deductions?.c80?.limit||150000)-(data.deductions?.c80?.used||0)});
      const res=await AIService.askForJSON(`Act as Indian Tax CA. Generate 3 specific tax-saving actions for FY 2025-26. Output JSON array only: [{"action":"...","section":"...","savings":"...","deadline":"..."}]`,ctx);
      setAdviceCards(res);
      localStorage.setItem("tax_audit_advice",JSON.stringify(res));
      setIsRateLimited(false);
    }catch(e){
      if(e.message?.includes("429")){setIsRateLimited(true);showToast("Rate limit reached. Wait 60s.","error");setTimeout(()=>setIsRateLimited(false),60000);}
      else showToast("AI Service Unavailable.","error");
    }finally{setAiLoading(false);}
  };

  return (
    <div className="space-y-6 pb-4 animate-in fade-in">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h2 className="text-2xl font-bold text-white mb-2">Tax Audit</h2>
          <div className="flex flex-wrap gap-2">
            <span className="text-[10px] font-bold px-2 py-1 rounded-md bg-white/5 text-slate-400 border border-white/10 flex items-center gap-1">
              <Wand2 className="w-3 h-3"/>{transactions.length} transactions
            </span>
            {userPersona.map(tag=>(
              <span key={tag} className="text-[10px] font-bold px-2 py-1 rounded-md bg-blue-500/10 text-blue-200 border border-blue-500/20 flex items-center gap-1">
                <UserCog className="w-3 h-3"/>{tag}
              </span>
            ))}
          </div>
        </div>
        <div className="flex gap-2">
          <button onClick={()=>window.print()} className="p-2 bg-white/10 rounded-full hover:bg-white/20 text-slate-300 transition-colors">
            <Printer className="w-4 h-4"/>
          </button>
          <button onClick={()=>setShowWizard(true)} className="p-2 bg-white/10 rounded-full hover:bg-white/20 text-white transition-colors">
            <Edit3 className="w-4 h-4"/>
          </button>
        </div>
      </div>

      {/* Hero */}
      <div className="bg-gradient-to-r from-blue-600 to-indigo-600 p-px rounded-[2rem] shadow-2xl">
        <div className="bg-slate-900/60 backdrop-blur-md rounded-[1.9rem] p-5 grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[
            {label:"Taxable Income",value:fmtC(data.recommendedTaxable),sub:`FY ${data.fiscalYear}`,col:"text-white"},
            {label:"Est. Tax Liability",value:fmtC(data.recommendedTax),sub:data.isNewCheaper?"New Regime":"Old Regime",col:"text-rose-300"},
            {label:"Regime Saves",value:fmtC(Math.abs((data.taxNew||0)-(data.taxOld||0))),sub:data.isNewCheaper?"vs Old Regime":"vs New Regime",col:"text-emerald-300"},
            {label:"Data Integrity",value:`${integrityScore}%`,sub:integrityLabel,col:integrityColor},
          ].map(s=>(
            <div key={s.label}>
              <p className="text-[10px] font-bold text-white/50 uppercase tracking-wider mb-1">{s.label}</p>
              <p className={`text-2xl font-black ${s.col}`}>{s.value}</p>
              {s.sub&&<p className="text-[10px] text-white/40 mt-0.5">{s.sub}</p>}
            </div>
          ))}
        </div>
      </div>

      {/* Tab nav */}
      <div className="flex gap-1 p-1 rounded-2xl bg-white/5 border border-white/8">
        {AUDIT_TABS.map(t=>{
          const Icon=t.icon;
          return (
            <button key={t.id} onClick={()=>setTab(t.id)}
              className={`flex-1 flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl text-xs font-semibold transition-all
                ${tab===t.id?"bg-white/10 text-white shadow-sm":"text-slate-400 hover:text-slate-200"}`}>
              <Icon className="w-3.5 h-3.5 shrink-0"/>
              <span className="hidden sm:inline">{t.label}</span>
            </button>
          );
        })}
      </div>

      {/* ── Overview ── */}
      {tab==="overview"&&(
        <div className="space-y-5">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div className="rounded-2xl border border-white/10 p-5">
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4 flex items-center gap-2">
                <Scale className="w-4 h-4"/>5 Heads of Income
              </h3>
              <div className="space-y-0">
                {[
                  {l:"1. Salary",v:data.heads?.salary||0},
                  {l:"2. House Property",v:data.heads?.houseProperty||0},
                  {l:"3. Business",v:data.heads?.business||0},
                  {l:"4. Capital Gains",v:data.heads?.capitalGains||0},
                  {l:"5. Other Sources",v:data.heads?.other||0},
                ].map(item=>(
                  <div key={item.l} className="flex justify-between py-2.5 border-b border-white/5 last:border-0">
                    <span className="text-sm text-slate-300">{item.l}</span>
                    <span className="text-sm font-semibold text-white">{fmt(item.v)}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="rounded-2xl border border-white/10 p-5">
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4 flex items-center gap-2">
                <Target className="w-4 h-4"/>Deductions (Old Regime)
              </h3>
              <DeductionBar label="80C Investments" used={data.deductions?.c80?.used||0} limit={150000} color="bg-cyan-500"/>
              <DeductionBar label="80D Health Insurance" used={data.deductions?.d80?.used||0} limit={75000} color="bg-pink-500"/>
              <DeductionBar label="NPS (80CCD 1B)" used={data.deductions?.nps?.used||0} limit={50000} color="bg-purple-500"/>
            </div>
          </div>

          {/* Integrity bar */}
          <div className="rounded-2xl border border-white/10 p-5 flex items-center gap-4">
            <ShieldAlert className={`w-6 h-6 ${integrityScore<80?"text-amber-500":"text-emerald-500"} shrink-0`}/>
            <div className="flex-1">
              <div className="flex justify-between items-center mb-2">
                <h4 className="text-sm font-bold text-white">Data Integrity Score</h4>
                <div className="text-right">
                  <span className={`text-xl font-black ${integrityColor}`}>{integrityScore}%</span>
                  <p className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">{integrityLabel}</p>
                </div>
              </div>
              <div className="h-2 w-full bg-black/40 rounded-full overflow-hidden">
                <div className="h-full bg-emerald-500 transition-all duration-700" style={{width:`${integrityScore}%`}}/>
              </div>
            </div>
          </div>

          {/* File ITR CTA */}
          <div className="rounded-2xl border border-indigo-500/20 bg-indigo-500/5 p-5 flex items-center justify-between gap-4">
            <div>
              <p className="font-bold text-white mb-1">Ready to file your return?</p>
              <p className="text-xs text-slate-400">
                Estimated tax: <span className="text-white font-semibold">{fmtC(data.recommendedTax)}</span>
                {data.isNewCheaper&&` · Save ${fmtC((data.taxOld||0)-(data.taxNew||0))} with New Regime`}
              </p>
            </div>
            <button onClick={()=>setActiveTab(TABS.ITR_FILING)}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-500 hover:bg-indigo-400 text-white text-sm font-bold transition-all shrink-0 shadow-lg shadow-indigo-500/20">
              File ITR<ArrowRight className="w-4 h-4"/>
            </button>
          </div>
        </div>
      )}

      {/* ── YoY Progress ── */}
      {tab==="yoy"&&(
        <div className="space-y-4">
          <div>
            <h3 className="text-base font-bold text-white mb-1">Year-over-Year Progress</h3>
            <p className="text-xs text-slate-400">Income, tax, and investment trends across financial years from your transaction history.</p>
          </div>
          <YoYSection transactions={transactions}/>
        </div>
      )}

      {/* ── Regime Comparison ── */}
      {tab==="regime"&&(
        <div className="space-y-4">
          <div>
            <h3 className="text-base font-bold text-white mb-1">New vs Old Regime</h3>
            <p className="text-xs text-slate-400">Side-by-side comparison based on your estimated income and deductions.</p>
          </div>
          <RegimeComparison income={data.sources?.total||0} deductions={totalDeductions}/>
        </div>
      )}

      {/* ── AI Consultant ── */}
      {tab==="ai"&&(
        <div className="rounded-2xl border border-white/10 bg-[#0f172a] p-6 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-64 h-64 bg-emerald-500/5 blur-[80px] rounded-full pointer-events-none"/>
          <div className="relative z-10">
            <div className="flex justify-between items-start mb-6">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <Bot className="w-5 h-5 text-emerald-400"/>
                  <h3 className="font-bold text-white text-lg">AI Consultant</h3>
                </div>
                <p className="text-xs text-slate-400">Tailored for {userPersona[0]}</p>
              </div>
              <div className="flex gap-2">
                {adviceCards.length>0&&!aiLoading&&(
                  <button onClick={()=>{localStorage.removeItem("tax_audit_advice");setAdviceCards([]);}}
                    className="p-2 bg-white/5 hover:bg-white/10 rounded-xl text-slate-400 hover:text-white transition-all border border-white/5" title="Clear cache">
                    <RefreshCw className="w-4 h-4"/>
                  </button>
                )}
                <button onClick={getAdvice} disabled={aiLoading||isRateLimited}
                  className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2
                    ${isRateLimited?"bg-rose-900/50 text-rose-300 cursor-not-allowed border border-rose-500/30"
                      :"bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-900/30"}`}>
                  {aiLoading?<Loader2 className="w-4 h-4 animate-spin"/>:<Sparkles className="w-4 h-4"/>}
                  {isRateLimited?"Limit Reached":aiLoading?"Analyzing...":adviceCards.length>0?"Refresh":"Identify Savings"}
                </button>
              </div>
            </div>
            {!aiLoading&&adviceCards.length===0&&(
              <div className="text-center py-8 text-slate-500 text-xs border border-dashed border-slate-700 rounded-xl">
                {isRateLimited?"Rate limit reached. Please wait ~60 seconds.":"Tap 'Identify Savings' to generate your personalised tax report."}
              </div>
            )}
            {adviceCards.length>0&&(
              <div className="grid gap-3">
                {adviceCards.map((card,i)=><TaxActionCard key={i} {...card}/>)}
              </div>
            )}
          </div>
        </div>
      )}

      <p className="text-[10px] text-slate-600 text-center pt-4 border-t border-white/5">
        Estimates based on available transaction data for educational purposes only.
      </p>

      <ProfileWizard isOpen={showWizard} onClose={()=>setShowWizard(false)}
        initialData={taxProfile} detectedValues={detectedValues} onSave={onUpdateProfile}/>
    </div>
  );
};

export default AuditPage;
