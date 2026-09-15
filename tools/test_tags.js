const fs = require('fs');
const ROOT = __dirname + '/..';
const html = fs.readFileSync(ROOT + '/index.html','utf8');
const script = html.match(/<script>([\s\S]*)<\/script>/)[1];
const SR = 48000;
const ctxStub = { sampleRate: SR, createBuffer:(c,n,s)=>{const d=new Float32Array(n);
  return {length:n,duration:n/s,getChannelData:()=>d};} };
function grab(n){
  const m = script.match(new RegExp('function '+n+'\\s*\\([\\s\\S]*?\\n  \\}','m'));
  if(!m) throw new Error('brak '+n); return m[0];
}
const consts = script.match(/const BANK_SR = [\s\S]*?const BANK_EPOCHS = .*?;/)[0];
const api = new Function('ctxStub','atob',[
  'const lerp=(a,b,t)=>a+(b-a)*t;',
  'let ctx=ctxStub,bank=null,bankSig=null;',
  consts, 'const SIG_LEN=48;',
  grab('decodeBank'), grab('buildSignatures'), grab('pickGrain'),
  grab('breathEnv'), grab('buildPurrCycle'),
  'bank=decodeBank(); bankSig=buildSignatures();',
  'return {buildPurrCycle,breathEnv,BANK_EPOCHS,bank};'
].join('\n'))(ctxStub, s=>Buffer.from(s,'base64').toString('binary'));

// ---------- tag distribution sanity ----------
const E = api.BANK_EPOCHS;
console.log('epok:', E.length, '| pola:', E[0].length);
const amps = E.map(r=>r[2]), bris = E.map(r=>r[3]);
const stat = a => `${Math.min(...a)}..${Math.max(...a)} sr=${(a.reduce((x,y)=>x+y,0)/a.length).toFixed(1)}`;
console.log('rangi amplitudy :', stat(amps));
console.log('rangi jasnosci  :', stat(bris));

// ---------- spectral brightness of the render vs mood ----------
function bandRatio(d, sr){
  // energy 200-2000 Hz over 25-200 Hz, via Goertzel probes
  const g = f => { const k=2*Math.cos(2*Math.PI*f/sr); let s1=0,s2=0;
    const n=Math.min(d.length,sr*2);
    for(let i=0;i<n;i++){const s0=d[i]+k*s1-s2;s2=s1;s1=s0;}
    return Math.max(0,s1*s1+s2*s2-k*s1*s2)/(n*n); };
  let lo=0, hi=0;
  for(const f of [30,50,80,120,160,200]) lo+=g(f);
  for(const f of [300,450,650,900,1300,1800]) hi+=g(f);
  return hi/(lo+hi+1e-20);
}

console.log('\nJASNOSC RENDERU WOBEC SUWAKA NASTROJU:');
for(const mood of [0, 0.25, 0.5, 0.75, 1.0]){
  const b = api.buildPurrCycle({duration:1.8, f0:25.5+mood*7, mood:mood, sub:0.2});
  const d = b.getChannelData(0);
  console.log(`  nastroj ${mood.toFixed(2)} -> jasnosc ${bandRatio(d,SR).toFixed(4)}`);
}

// ---------- does grain level track the breath envelope? ----------
console.log('\nCZY POZIOM ZIAREN SLEDZI ODDECH:');
const b = api.buildPurrCycle({duration:1.8, f0:28, mood:0.4, sub:0});
const d = b.getChannelData(0);
const NB = 10, blk = Math.floor(d.length/NB);
const rmsB = [], envB = [];
for(let k=0;k<NB;k++){
  let s=0; for(let i=k*blk;i<(k+1)*blk;i++) s+=d[i]*d[i];
  rmsB.push(Math.sqrt(s/blk));
  envB.push(api.breathEnv((k+0.5)/NB, 0.60));
}
const mx = Math.max(...rmsB);
let sx=0,sy=0,sxx=0,syy=0,sxy=0;
for(let k=0;k<NB;k++){ const x=envB[k], y=rmsB[k]/mx;
  sx+=x; sy+=y; sxx+=x*x; syy+=y*y; sxy+=x*y; }
const r = (NB*sxy-sx*sy)/Math.sqrt((NB*sxx-sx*sx)*(NB*syy-sy*sy));
for(let k=0;k<NB;k++){
  console.log(`  ${((k+0.5)/NB).toFixed(2)}  oddech ${envB[k].toFixed(3)}  poziom ${(rmsB[k]/mx).toFixed(3)}  `
    + '#'.repeat(Math.round(rmsB[k]/mx*26)));
}
console.log('  korelacja poziom/oddech: r =', r.toFixed(3));

// ---------- repetition + cost ----------
const a1 = api.buildPurrCycle({duration:1.8,f0:28,mood:0.4,sub:0.2}).getChannelData(0);
const a2 = api.buildPurrCycle({duration:1.8,f0:28,mood:0.4,sub:0.2}).getChannelData(0);
let dot=0,na=0,nb=0;
for(let i=0;i<a1.length;i++){ dot+=a1[i]*a2[i]; na+=a1[i]*a1[i]; nb+=a2[i]*a2[i]; }
console.log('\nkorelacja dwoch cykli (te same ustawienia):', (dot/Math.sqrt(na*nb)).toFixed(3));
const t0=Date.now();
for(let v=0;v<6;v++) api.buildPurrCycle({duration:1.8,f0:28,mood:0.4,sub:0.2});
console.log('regeneracja 6 wariantow:', Date.now()-t0, 'ms');
