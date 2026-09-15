// Runs the whole page script under browser stubs: catches missing functions,
// bad references and slider handlers that throw — the things a bare syntax
// check sails straight past.
const fs = require('fs');
const file = process.argv[2] || '/home/claude/bilateral-sounds-v4.html';
const html = fs.readFileSync(file, 'utf8');
const script = html.match(/<script>([\s\S]*)<\/script>/)[1];

const listeners = {};
const els = {};
const mkEl = id => ({
  id, value: '50', textContent: '', innerHTML: '',
  classList: { add(){}, remove(){} },
  addEventListener: (ev, fn) => { (listeners[id] = listeners[id] || {})[ev] = fn; }
});
global.document = { getElementById: id => els[id] || (els[id] = mkEl(id)) };
global.atob = s => Buffer.from(s, 'base64').toString('binary');

const SR = 48000;
const param = v => ({ value: v, setTargetAtTime(){}, setValueAtTime(){},
                      linearRampToValueAtTime(){}, exponentialRampToValueAtTime(){} });
const node = (extra={}) => Object.assign({ connect(){}, disconnect(){}, start(){}, stop(){} }, extra);

let started = 0, buffersMade = 0;
class FakeCtx {
  constructor(){ this.sampleRate = SR; this.currentTime = 0; this.destination = node(); }
  createGain(){ return node({ gain: param(1) }); }
  createStereoPanner(){ return node({ pan: param(0) }); }
  createOscillator(){ return node({ frequency: param(1), type:'sine', detune: param(0),
                                    start(){ started++; }, stop(){} }); }
  createWaveShaper(){ return node({ curve: null }); }
  createBiquadFilter(){ return node({ type:'lowpass', frequency: param(1000), Q: param(1) }); }
  createDelay(){ return node({ delayTime: param(0) }); }
  createBufferSource(){ return node({ buffer:null, loop:false, playbackRate: param(1),
                                      start(){ started++; }, stop(){} }); }
  createConstantSource(){ return node({ offset: param(0), start(){ started++; }, stop(){} }); }
  createBuffer(c,n,s){ buffersMade++; const d = new Float32Array(n);
                       return { length:n, duration:n/s, sampleRate:s, getChannelData:()=>d }; }
  close(){}
}
global.window = { AudioContext: FakeCtx };

const timers = [];
global.setInterval = (fn) => { timers.push(fn); return timers.length; };
global.setTimeout  = (fn) => { timers.push(fn); return timers.length; };
global.clearInterval = () => {};
global.clearTimeout  = () => {};

let fails = 0;
const step = (label, fn) => {
  try { fn(); console.log('  OK   ' + label); }
  catch(e){ fails++; console.log('  FAIL ' + label + ' -> ' + e.constructor.name + ': ' + e.message);
            console.log('       ' + (e.stack.split('\n')[1]||'').trim()); }
};

console.log('TEST: ' + file.split('/').pop() + '\n');
step('zaladowanie skryptu', () => new Function(script)());
step('klik play', () => listeners['playBtn'].click());

const sliders = ['mixSlider','panSlider','depthSlider','shapeSlider','volSlider',
                 'moodSlider','distSlider','subSlider','rainSlider'];
for(const s of sliders){
  step('suwak ' + s + ' (input)', () => {
    if(!listeners[s] || !listeners[s].input) throw new Error('brak handlera input');
    els[s].value = '70';
    listeners[s].input();
  });
}
for(const s of ['moodSlider','subSlider']){
  step('suwak ' + s + ' (change)', () => {
    if(listeners[s] && listeners[s].change) listeners[s].change();
  });
}
step('timery tickuja', () => { for(const t of timers.slice(0,6)) t(); });
step('klik stop', () => listeners['playBtn'].click());
step('ponowny start', () => listeners['playBtn'].click());

console.log('\nwezly uruchomione: ' + started + ' | bufory utworzone: ' + buffersMade);
console.log(fails ? `\n${fails} BLEDOW` : '\nwszystko przeszlo');
process.exit(fails ? 1 : 0);
