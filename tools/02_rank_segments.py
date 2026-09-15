import wave, numpy as np, statistics, json
from scipy import signal

import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def P(*a): return os.path.join(ROOT, *a)

W = wave.open(P('source-audio','nagranie.wav'))
SR = W.getframerate()
d = np.frombuffer(W.readframes(W.getnframes()), dtype=np.int16).astype(float)/32768

WIN = int(SR*1.0)
HOP = int(SR*0.25)
nfr = (len(d)-WIN)//HOP
hann = np.hanning(WIN)
f = np.fft.rfftfreq(WIN, 1/SR)

f_, t_, Sx = signal.spectrogram(d, SR, nperseg=2048, noverlap=1024)
flux = np.concatenate([[0], np.maximum(0, np.diff(10*np.log10(Sx+1e-14), axis=1)).mean(axis=0)])

rows = []
for i in range(nfr):
    a = i*HOP; seg = d[a:a+WIN]; t0 = a/SR
    rms = np.sqrt((seg**2).mean())
    if rms < 1e-6: continue
    S = np.abs(np.fft.rfft(seg*hann))+1e-12
    cep = np.fft.irfft(np.log(S))
    lo, hi = int(SR/45), int(SR/20)
    q = lo+int(np.argmax(cep[lo:hi])); f0 = SR/q
    hscore = float(cep[q]) - float(np.median(cep[lo:hi]))
    def at(fq):
        m = (f > fq-2.5) & (f < fq+2.5)
        return 20*np.log10(S[m].max()) if m.any() else -120.0
    hs = [at(f0*h) for h in range(1,6)]
    h1 = hs[0]-max(hs)
    m = (t_ >= t0) & (t_ < t0+1.0)
    tr = float(flux[m].max()) if m.any() else 0.0
    low  = 10*np.log10(np.mean(S[(f>25)&(f<300)]**2))
    high = 10*np.log10(np.mean(S[(f>2000)&(f<8000)]**2))
    rows.append(dict(t=t0, lvl=20*np.log10(rms), f0=f0, h=hscore,
                     h1=h1, tr=tr, tilt=low-high))

def z(vals):
    v = np.array(vals, float); s = v.std()
    return (v-v.mean())/(s if s > 1e-9 else 1)

zl  = z([r['lvl']  for r in rows])
zh  = z([r['h']    for r in rows])
zh1 = z([r['h1']   for r in rows])
zt  = z([r['tilt'] for r in rows])
ztr = z([r['tr']   for r in rows])

for i, r in enumerate(rows):
    # weights: harmonic clarity and a surviving fundamental matter most;
    # transients are penalised, level and spectral tilt are supporting.
    r['score'] = (1.1*zh[i] + 1.0*zh1[i] + 0.6*zl[i] + 0.5*zt[i] - 0.9*ztr[i])
    if not (22 < r['f0'] < 42):
        r['score'] -= 3.0

scores = np.array([r['score'] for r in rows])
thr = float(np.percentile(scores, 70))

runs, cur = [], None
for r in rows:
    if r['score'] > thr:
        cur = [r] if cur is None else cur+[r]
    else:
        if cur and len(cur)*0.25 >= 1.0: runs.append(cur)
        cur = None
if cur and len(cur)*0.25 >= 1.0: runs.append(cur)

out = []
for run in runs:
    t0 = run[0]['t']; t1 = run[-1]['t']+1.0
    out.append(dict(
        t0=round(t0,2), t1=round(t1,2), dur=round(t1-t0,2),
        f0=round(statistics.median(r['f0'] for r in run),1),
        f0sd=round(statistics.pstdev([r['f0'] for r in run]) if len(run)>1 else 0,1),
        h1=round(statistics.median(r['h1'] for r in run),1),
        lvl=round(statistics.median(r['lvl'] for r in run),1),
        tr=round(statistics.median(r['tr'] for r in run),1),
        score=round(statistics.mean(r['score'] for r in run),2)))

out.sort(key=lambda s: -s['score'])
total = sum(s['dur'] for s in out)

print(f'ZNALEZIONO {len(out)} FRAGMENTOW, razem {total:.1f} s '
      f'({total/(len(d)/SR)*100:.0f}% nagrania)\n')
print(f"{'#':>2} {'od':>7} {'do':>7} {'dl':>5} {'f0':>6} {'±':>4} {'H1':>6} {'poziom':>7} {'ocena':>6}")
print('-'*60)
for i,s in enumerate(out,1):
    print(f"{i:>2} {s['t0']:7.2f} {s['t1']:7.2f} {s['dur']:5.2f} {s['f0']:6.1f} "
          f"{s['f0sd']:4.1f} {s['h1']:6.1f} {s['lvl']:7.1f} {s['score']:6.2f}")

json.dump(out, open(P('data','segments.json'),'w'), indent=1)
print('\nchronologicznie:')
for s in sorted(out, key=lambda x: x['t0']):
    print(f"  {s['t0']:6.2f}-{s['t1']:6.2f} s  ({s['dur']:4.1f}s, f0={s['f0']:.1f} Hz)")
