import numpy as np, wave, subprocess, glob, json, base64
from scipy import signal

import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def P(*a): return os.path.join(ROOT, *a)

SR_OUT = 8000
seg_paths = sorted(glob.glob(P('source-audio','fragmenty','*.wav')))

def load_8k(p):
    subprocess.run(f"ffmpeg -hide_banner -loglevel error -i '{p}' -ac 1 -ar {SR_OUT} "
                   f"-af 'aresample=resampler=soxr' -c:a pcm_s16le /tmp/seg8.wav -y", shell=True)
    w = wave.open('/tmp/seg8.wav')
    return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(float)/32768

def local_period(x, sr):
    """Median period over the segment, via FFT autocorrelation."""
    n = 1 << int(np.ceil(np.log2(len(x)*2)))
    F = np.fft.rfft(x-x.mean(), n)
    r = np.fft.irfft(F*np.conj(F))[:len(x)]
    r /= r[0] + 1e-12
    lo, hi = int(sr/40), int(sr/22)          # 22-40 Hz
    return lo + int(np.argmax(r[lo:hi]))

def find_epochs(x, sr, T):
    """Glottal closure instants: peaks of the negative derivative of the
       low-passed signal, spaced at roughly one period."""
    b, a = signal.butter(4, 300/(sr/2), 'low')
    lp = signal.filtfilt(b, a, x)
    d = -np.diff(lp, prepend=lp[0])          # closure = steep negative slope
    d = signal.filtfilt(*signal.butter(2, 400/(sr/2), 'low'), d)
    pk, _ = signal.find_peaks(d, distance=int(T*0.72))
    return pk

bank = []          # concatenated audio
epochs = []        # (index into bank, period at that epoch)
meta = []

cursor = 0
for p in seg_paths:
    x = load_8k(p)
    # gentle DC block
    x = signal.filtfilt(*signal.butter(2, 12/(SR_OUT/2), 'high'), x)
    T = local_period(x, SR_OUT)
    ep = find_epochs(x, SR_OUT, T)
    if len(ep) < 4:
        continue
    iv = np.diff(ep)
    keep = (iv > T*0.6) & (iv < T*1.6)
    good = float(keep.mean())

    bank.append(x.astype(np.float32))
    for i in range(len(ep)-1):
        per = ep[i+1]-ep[i]
        if T*0.6 < per < T*1.6 and ep[i] > T and ep[i]+2*T < len(x):
            epochs.append((cursor + int(ep[i]), int(per)))
    meta.append(dict(file=p.split('/')[-1], f0=round(SR_OUT/T,1),
                     epochs=len(ep), regular=round(good,3), dur=round(len(x)/SR_OUT,2)))
    cursor += len(x)

audio = np.concatenate(bank)

# ---- tag every epoch with what actually varies between grains ----
# Amplitude and brightness turn out to be independent (r = -0.03), so they
# give two usable selection axes. Percentile ranks rather than raw values,
# so the selection windows in the engine cover an even share of the bank.
amps, bris = [], []
for e, per in epochs:
    a = e-per; L = 2*per
    g = audio[a:a+L] if (a >= 0 and a+L < len(audio)) else np.zeros(max(L,2))
    amps.append(float(np.sqrt((g**2).mean())))
    S = np.abs(np.fft.rfft(g*np.hanning(len(g))))
    fq = np.fft.rfftfreq(len(g), 1/SR_OUT)
    lo = float(np.sum(S[(fq > 20) & (fq <= 200)]**2))
    hi = float(np.sum(S[(fq > 200) & (fq < 2000)]**2))
    bris.append(hi/(lo+hi+1e-20))

def pct_rank(v):
    v = np.asarray(v)
    r = np.argsort(np.argsort(v)).astype(float)
    return np.round(r/max(len(v)-1, 1)*100).astype(int)

pa, pb = pct_rank(amps), pct_rank(bris)
tagged = [[int(e), int(p), int(a), int(b)]
          for (e, p), a, b in zip(epochs, pa, pb)]

print()
print('TAGI ZIAREN')
print('  amplituda : min %.4f  mediana %.4f  max %.4f  (%.1fx)'
      % (min(amps), float(np.median(amps)), max(amps), max(amps)/max(min(amps),1e-9)))
print('  jasnosc   : min %.4f  mediana %.4f  max %.4f  (%.1fx)'
      % (min(bris), float(np.median(bris)), max(bris), max(bris)/max(min(bris),1e-9)))
print('  korelacja amplituda/jasnosc: %+.3f' % np.corrcoef(amps, bris)[0,1])

print('SEGMENTY:')
print(f"{'plik':<34} {'f0':>6} {'epok':>5} {'regul.':>7}")
for m in meta:
    print(f"  {m['file']:<32} {m['f0']:>6.1f} {m['epochs']:>5} {m['regular']:>7.1%}")

print()
print('BANK ZIAREN')
print('  audio        :', len(audio), 'probek =', round(len(audio)/SR_OUT,2), 's @', SR_OUT, 'Hz')
print('  epok uzytych :', len(epochs))
pers = np.array([e[1] for e in epochs])
print('  okres        : mediana', int(np.median(pers)), 'probek =',
      round(SR_OUT/np.median(pers),1), 'Hz')
print('  rozrzut f0   :', round(SR_OUT/np.percentile(pers,90),1), '-',
      round(SR_OUT/np.percentile(pers,10),1), 'Hz')

# normalise the bank
peak = np.abs(audio).max()
audio = audio/peak*0.92
pcm = (audio*32767).astype('<i2')

print('  rozmiar PCM  :', round(pcm.nbytes/1024,1), 'KB -> base64',
      round(pcm.nbytes*4/3/1024,1), 'KB')

np.save(P('data','bank_audio.npy'), pcm)
json.dump(tagged, open(P('data','bank_epochs.json'),'w'))
json.dump(meta, open(P('data','bank_meta.json'),'w'), indent=1)

b64 = base64.b64encode(pcm.tobytes()).decode('ascii')
open(P('data','bank_b64.txt'),'w').write(b64)
print('  base64       :', round(len(b64)/1024,1), 'KB')
