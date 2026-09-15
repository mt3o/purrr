import wave, numpy as np
from scipy import signal

import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def P(*a): return os.path.join(ROOT, *a)

W = wave.open(P('source-audio','nagranie.wav'))
SR = W.getframerate()
d = np.frombuffer(W.readframes(W.getnframes()), dtype=np.int16).astype(float)/32768

WIN = int(SR*1.0)       # 1 s analysis window
HOP = int(SR*0.25)      # 0.25 s hop
nfr = (len(d)-WIN)//HOP

# ---- precompute a broadband transient detector (spectral flux) ----
f_, t_, Sx = signal.spectrogram(d, SR, nperseg=2048, noverlap=1024)
Sxdb = 10*np.log10(Sx+1e-14)
flux = np.maximum(0, np.diff(Sxdb, axis=1)).mean(axis=0)
flux = np.concatenate([[0], flux])
flux_t = t_

rows = []
hann = np.hanning(WIN)

for i in range(nfr):
    a = i*HOP
    seg = d[a:a+WIN]
    t0 = a/SR

    rms = np.sqrt((seg**2).mean())
    if rms < 1e-6:
        continue
    lvl = 20*np.log10(rms)

    # --- cepstrum: harmonic spacing + how clearly harmonic it is ---
    s = seg*hann
    S = np.abs(np.fft.rfft(s))+1e-12
    cep = np.fft.irfft(np.log(S))
    lo, hi = int(SR/45), int(SR/20)          # search 20-45 Hz
    q = lo + int(np.argmax(cep[lo:hi]))
    f0 = SR/q
    harmonicity = float(cep[q])
    # baseline of the cepstrum in that region, so harmonicity is relative
    base = float(np.median(cep[lo:hi]))
    hscore = harmonicity - base

    # --- harmonic ladder: does the fundamental survive? ---
    f = np.fft.rfftfreq(WIN, 1/SR)
    def at(fq):
        m = (f > fq-2.5) & (f < fq+2.5)
        return 20*np.log10(S[m].max()) if m.any() else -120
    hs = [at(f0*h) for h in range(1,6)]
    ref = max(hs)
    h1rel = hs[0]-ref

    # --- transient contamination in this window ---
    m = (flux_t >= t0) & (flux_t < t0+1.0)
    tr = float(flux[m].max()) if m.any() else 0.0

    # --- band balance: purr energy should sit low ---
    lowE  = 10*np.log10(np.mean(np.abs(np.fft.rfft(s))[(f>25)&(f<300)]**2)+1e-20)
    highE = 10*np.log10(np.mean(np.abs(np.fft.rfft(s))[(f>2000)&(f<8000)]**2)+1e-20)
    tilt = lowE - highE

    rows.append(dict(t=t0, lvl=lvl, f0=f0, h=hscore, h1=h1rel, tr=tr, tilt=tilt))

import statistics
lvls  = [r['lvl'] for r in rows]
hs_   = [r['h']   for r in rows]
trs   = [r['tr']  for r in rows]
tilts = [r['tilt'] for r in rows]

def pct(xs, p): return float(np.percentile(xs, p))

print('ROZKLAD METRYK')
print(f"  poziom  : p10={pct(lvls,10):6.1f}  mediana={pct(lvls,50):6.1f}  p90={pct(lvls,90):6.1f} dBFS")
print(f"  harmonic: p10={pct(hs_,10):6.3f}  mediana={pct(hs_,50):6.3f}  p90={pct(hs_,90):6.3f}")
print(f"  transj. : p50={pct(trs,50):6.2f}  p90={pct(trs,90):6.2f}  max={max(trs):6.2f}")
print(f"  tilt    : p10={pct(tilts,10):6.1f}  mediana={pct(tilts,50):6.1f} dB")
print()

# ---- thresholds from the file's own distribution ----
LVL_MIN  = max(pct(lvls,45), -40)
H_MIN    = pct(hs_, 55)
TR_MAX   = pct(trs, 75)
TILT_MIN = pct(tilts, 40)

print(f'PROGI: poziom>{LVL_MIN:.1f} dBFS, harmonicznosc>{H_MIN:.3f}, transjent<{TR_MAX:.2f}, tilt>{TILT_MIN:.1f} dB')
print()

for r in rows:
    r['ok'] = (r['lvl'] > LVL_MIN and r['h'] > H_MIN and
               r['tr'] < TR_MAX and r['tilt'] > TILT_MIN and
               22 < r['f0'] < 42)

# ---- contiguous runs ----
runs = []
cur = None
for r in rows:
    if r['ok']:
        if cur is None: cur = [r]
        else: cur.append(r)
    else:
        if cur and len(cur)*0.25 >= 1.5: runs.append(cur)
        cur = None
if cur and len(cur)*0.25 >= 1.5: runs.append(cur)

print(f'ZNALEZIONO {len(runs)} FRAGMENTOW (>=1.5 s)\n')
print(f"{'od':>7} {'do':>7} {'dlug':>6} {'f0':>6} {'H1':>7} {'poziom':>7} {'harm':>6}")
print('-'*52)
summary = []
for run in runs:
    t0 = run[0]['t']; t1 = run[-1]['t']+1.0
    f0 = statistics.median(r['f0'] for r in run)
    h1 = statistics.median(r['h1'] for r in run)
    lv = statistics.median(r['lvl'] for r in run)
    hh = statistics.median(r['h'] for r in run)
    f0sd = statistics.pstdev([r['f0'] for r in run]) if len(run)>1 else 0
    summary.append((t0,t1,f0,h1,lv,hh,f0sd))
    print(f'{t0:7.2f} {t1:7.2f} {t1-t0:6.2f} {f0:6.1f} {h1:7.1f} {lv:7.1f} {hh:6.3f}')

total = sum(t1-t0 for t0,t1,*_ in summary)
print('-'*52)
print(f'razem uzytecznego materialu: {total:.1f} s z {len(d)/SR:.1f} s ({total/(len(d)/SR)*100:.0f}%)')

# rank by how well the fundamental survives, then by length
print('\nNAJLEPSZE DO EKSTRAKCJI ZIAREN (H1 najmniej stlumione):')
ranked = sorted(summary, key=lambda s: (s[3], -(s[1]-s[0])), reverse=True)[:10]
for t0,t1,f0,h1,lv,hh,sd in ranked:
    print(f'  {t0:6.2f}-{t1:6.2f} s  ({t1-t0:4.1f}s)  f0={f0:4.1f} Hz  H1={h1:5.1f} dB  stab.f0=±{sd:.1f}')

np.save(P('data','segments.npy'), np.array(summary))
