  /* ---------------------------------------------------------------
     Purr — granular resynthesis from a real recording  (v4)

     The bank below is a real cat purr, cut to the passages where the
     harmonic structure is cleanest, resampled to 8 kHz (99.95% of the
     energy sits under 4 kHz) and split at glottal closure instants.

     Playback is PSOLA-style: two-period Hann grains centred on each
     epoch, overlap-added at whatever period the mood slider asks for.
     Grains normally advance sequentially through the source so the
     waveform stays continuous; every 8-20 grains the playhead jumps to
     a different epoch whose waveform *shape* matches the current one,
     which keeps the upper harmonics intact while preventing the 24 s of
     source material from ever being heard as a loop.

     The phone's input highpass removed the fundamental (H1 sat 10-18 dB
     below H3 in every take), so a sine at f0, locked to the grain
     envelope, is added back underneath. That is the one part of the purr
     that is still synthetic — and the part the microphone could not
     capture.
  --------------------------------------------------------------- */

  const BANK_SR = 8000;
  const BANK_B64 = "__BANK_B64__";
  // [sampleIndex, periodInSamples, amplitudeRank, brightnessRank]
  // The two ranks are percentiles over the whole bank. Amplitude and
  // brightness measured out as independent (r = -0.03), so they steer the
  // breath envelope and the mood slider without fighting each other.
  const BANK_EPOCHS = __BANK_EPOCHS__;

  let bank = null;          // Float32Array of the decoded bank
  let bankSig = null;       // per-epoch waveform signatures, for matched jumps

  function decodeBank(){
    const bin = atob(BANK_B64);
    const n = bin.length/2;
    const view = new DataView(new ArrayBuffer(bin.length));
    for(let i=0;i<bin.length;i++) view.setUint8(i, bin.charCodeAt(i));
    const out = new Float32Array(n);
    for(let i=0;i<n;i++) out[i] = view.getInt16(i*2, true)/32768;
    return out;
  }

  /* A short, length-normalised sketch of one period, used to find grains
     that can follow each other without a phase jolt. */
  const SIG_LEN = 48;
  function buildSignatures(){
    const m = BANK_EPOCHS.length;
    const sig = new Float32Array(m*SIG_LEN);
    for(let i=0;i<m;i++){
      const e = BANK_EPOCHS[i][0], per = BANK_EPOCHS[i][1];
      const a = Math.max(0, e - (per>>1));
      let norm = 0;
      for(let k=0;k<SIG_LEN;k++){
        const pos = a + k*(per-1)/(SIG_LEN-1);
        const i0 = pos|0, fr = pos-i0;
        const v = (bank[i0]||0)*(1-fr) + (bank[i0+1]||0)*fr;
        sig[i*SIG_LEN+k] = v;
        norm += v*v;
      }
      norm = Math.sqrt(norm);
      if(norm > 1e-9) for(let k=0;k<SIG_LEN;k++) sig[i*SIG_LEN+k] /= norm;
    }
    return sig;
  }

  /* Pick a grain that fits the moment: right period, amplitude near what the
     breath envelope is asking for, brightness near what the mood asks for —
     and out of those, one whose waveform follows the current grain cleanly.
     Windows are wide (±25 percentile); measured pool sizes stay near 100
     grains, so constraining on all three never starves the choice. */
  function pickGrain(idx, per, wantAmp, wantBright){
    const m = BANK_EPOCHS.length;
    const WA = 26, WB = 22;
    let best = [], loose = null, looseScore = 1e9;
    for(let j=0;j<m;j++){
      if(j === idx) continue;
      const E = BANK_EPOCHS[j];
      if(Math.abs(E[1]-per) > per*0.12) continue;
      const da = Math.abs(E[2]-wantAmp), db = Math.abs(E[3]-wantBright);
      if(da+db < looseScore){ looseScore = da+db; loose = j; }
      if(da > WA || db > WB) continue;
      let dot = 0;
      for(let k=0;k<SIG_LEN;k++) dot += bankSig[idx*SIG_LEN+k]*bankSig[j*SIG_LEN+k];
      // keep a wide shortlist: picking from 16 rather than 10 is what stops
      // successive cycles from converging on the same path through the bank
      if(best.length < 16){ best.push([dot,j]); best.sort((a,b)=>a[0]-b[0]); }
      else if(dot > best[0][0]){ best[0] = [dot,j]; best.sort((a,b)=>a[0]-b[0]); }
    }
    if(best.length) return best[(Math.random()*best.length)|0][1];
    if(loose !== null) return loose;              // nothing in window: nearest fit
    return (Math.random()*m)|0;
  }

  /* The breath envelope: t·e^(−kt), asymmetric, never quite silent. */
  function breathEnv(t, exhaleFrac){
    const shape = (u,k) => {
      const peakV = (1/k)*Math.exp(-1);
      return peakV > 0 ? (u*Math.exp(-k*u))/peakV : 0;
    };
    let v;
    if(t < exhaleFrac) v = shape(t/exhaleFrac, 2.6);
    else               v = shape((t-exhaleFrac)/(1-exhaleFrac), 3.2)*0.6;
    return v*0.94 + 0.06;
  }

  function buildPurrCycle(opts){
    const sr = ctx.sampleRate;
    const n  = Math.floor(sr * opts.duration);
    const buf = ctx.createBuffer(1, n, sr);
    const out = buf.getChannelData(0);

    const ratio = BANK_SR / sr;            // bank samples per output sample
    const EXH = 0.60;                      // exhale takes the longer share
    const P = sr / opts.f0;                // grain period in output samples

    // brightness target comes from the mood slider: a happier cat is a
    // brighter one, and brightness is a property of the recording, not a filter.
    // Each cycle gets its own small bias on both targets — without it, cycles
    // built at identical settings walk near-identical paths through the bank
    // and the whole thing starts sounding like a loop again.
    const biasB = (Math.random()-0.5)*16;
    const biasA = (Math.random()-0.5)*16;
    const wantBright = Math.round(14 + opts.mood*70 + biasB);

    let idx = (Math.random()*BANK_EPOCHS.length)|0;
    let pos = -P;
    let run = 0;
    let nextJump = 8 + ((Math.random()*12)|0);

    while(pos < n){
      const E = BANK_EPOCHS[idx];
      const e = E[0], per = E[1];
      const a = e - per;
      const L = 2*per;
      if(a < 0 || a+L >= bank.length){
        idx = (Math.random()*BANK_EPOCHS.length)|0;
        continue;
      }

      const Lout = Math.round(L/ratio);
      const start = Math.round(pos);
      for(let k=0;k<Lout;k++){
        const o = start + k;
        if(o < 0 || o >= n) continue;
        const sp = a + k*ratio;
        const i0 = sp|0, fr = sp-i0;
        const v = bank[i0]*(1-fr) + (bank[i0+1]||0)*fr;
        const w = 0.5 - 0.5*Math.cos(2*Math.PI*k/(Lout-1));
        out[o] += v*w;
      }

      pos += P;

      // what the next grain should look like at this point in the breath
      const tNext = Math.min(1, Math.max(0, pos/n));
      const env = breathEnv(tNext, EXH);
      const wantAmp = Math.round(env*100 + biasA);

      // stay sequential while the neighbouring grain still fits, so the
      // waveform runs on unbroken; otherwise pick a grain that does fit.
      // Brightness is checked here too — leaving it to the jump path only
      // let it drift freely and the mood slider stopped changing anything.
      const nxt = BANK_EPOCHS[(idx+1) % BANK_EPOCHS.length];
      const drifted = Math.abs(nxt[2]-wantAmp) > 30 || Math.abs(nxt[3]-wantBright) > 22;

      if(++run >= nextJump || drifted){
        run = 0;
        nextJump = 8 + ((Math.random()*12)|0);
        idx = pickGrain(idx, per, wantAmp, wantBright);
      } else {
        idx = (idx+1) % BANK_EPOCHS.length;
      }
    }

    /* Selection already carries part of the breath, so the gain envelope is
       applied at reduced depth — full depth on top of matched grains
       double-modulates and sounds pumped. */
    for(let i=0;i<n;i++){
      const env = breathEnv(i/n, EXH);
      out[i] *= 0.45 + 0.55*env;
    }

    /* ---- restore the fundamental the phone's highpass cut away ---- */
    if(opts.sub > 0){
      let follow = 0;
      const atk = 1 - Math.exp(-1/(sr*0.02));
      const rel = 1 - Math.exp(-1/(sr*0.12));
      const foll = new Float32Array(n);
      for(let i=0;i<n;i++){
        const av = Math.abs(out[i]);
        follow += (av > follow ? atk : rel) * (av - follow);
        foll[i] = follow;
      }
      let fmax = 0;
      for(let i=0;i<n;i++) if(foll[i] > fmax) fmax = foll[i];
      if(fmax > 1e-9){
        const w = 2*Math.PI*opts.f0/sr;
        for(let i=0;i<n;i++) out[i] += Math.sin(w*i) * (foll[i]/fmax) * opts.sub;
      }
    }

    /* ---- DC block ---- */
    let x1=0, y1=0;
    for(let i=0;i<n;i++){
      const x = out[i];
      const y = x - x1 + 0.995*y1;
      out[i] = y; x1 = x; y1 = y;
    }

    /* ---- normalise + taper the joins ---- */
    let peak = 0;
    for(let i=0;i<n;i++) peak = Math.max(peak, Math.abs(out[i]));
    if(peak > 0){ const g = 0.55/peak; for(let i=0;i<n;i++) out[i] *= g; }
    const edge = Math.floor(sr*0.015);
    for(let i=0;i<edge;i++){
      const g = i/edge;
      out[i] *= g; out[n-1-i] *= g;
    }
    return buf;
  }

  function regeneratePurrCycles(){
    const mood = parseFloat(moodSlider.value)/100;
    const sub  = parseFloat(subSlider.value)/100;
    purrCycles = [];
    for(let v=0; v<6; v++){
      const wobble = (Math.random()-0.5);
      purrCycles.push(buildPurrCycle({
        duration: lerp(2.05, 1.35, mood) + wobble*0.12,
        f0:       lerp(25.5, 32.5, mood)  + wobble*0.8,
        mood:     mood,
        sub:      sub
      }));
    }
  }
