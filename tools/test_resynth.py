import numpy as np, json, wave
from scipy import signal

import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def P(*a): return os.path.join(ROOT, *a)

SR = 8000
pcm = np.load(P('data','bank_audio.npy')).astype(np.float32)/32767
epochs = json.load(open(P('data','bank_epochs.json')))
print('bank:', len(pcm), 'probek,', len(epochs), 'epok')

def resynth(seconds, f0_target, subgain=0.0, seed=0):
    rng = np.random.default_rng(seed)
    n_out = int(SR*seconds)
    out = np.zeros(n_out + SR)
    P = SR/f0_target

    idx = rng.integers(0, len(epochs))
    pos = 0.0
    grains = 0
    run = 0
    while pos < n_out:
        e, per = epochs[idx]
        L = int(per*2)
        if e+L >= len(pcm):
            idx = rng.integers(0, len(epochs)); continue

        g = pcm[e:e+L]*np.hanning(L)
        p = int(pos)
        out[p:p+L] += g
        grains += 1

        # advance by the TARGET period, not the source period -> pitch shift
        pos += P

        # walk forward through the source for waveform continuity, but jump
        # to a random epoch of a similar period every few grains
        run += 1
        if run >= rng.integers(3, 9):
            run = 0
            cand = [j for j in range(len(epochs))
                    if abs(epochs[j][1]-per) < per*0.12]
            idx = cand[rng.integers(0, len(cand))] if cand else rng.integers(0, len(epochs))
        else:
            idx = (idx+1) % len(epochs)

    out = out[:n_out]

    # ---- restore the fundamental the phone's highpass removed ----
    if subgain > 0:
        # track the grain envelope so the sub follows the purr, not a drone
        env = np.abs(signal.hilbert(signal.filtfilt(
            *signal.butter(3, [40/(SR/2), 300/(SR/2)], 'band'), out)))
        env = signal.filtfilt(*signal.butter(2, 12/(SR/2), 'low'), env)
        env /= env.max()+1e-12
        t = np.arange(n_out)/SR
        # phase-locked to the grain rate so it reinforces rather than beats
        sub = np.sin(2*np.pi*f0_target*t)
        out = out + sub*env*subgain

    m = np.abs(out).max()
    return out/m*0.9 if m > 0 else out, grains

def harmonics(x, f0, label):
    N = 1 << int(np.floor(np.log2(len(x))))
    S = np.abs(np.fft.rfft(x[:N]*np.hanning(N)))+1e-12
    f = np.fft.rfftfreq(N, 1/SR)
    def at(fq):
        m = (f > fq-2) & (f < fq+2)
        return 20*np.log10(S[m].max())
    hs = [at(f0*h) for h in range(1,7)]
    ref = max(hs)
    print(f'  {label:<28}', '  '.join(f'H{i+1}:{v-ref:6.1f}' for i,v in enumerate(hs)))

print('\nHARMONICZNE PO RESYNTEZIE (f0=28 Hz):')
src = pcm[:SR*8]
harmonics(src, 28.0, 'material zrodlowy')
for sg in [0.0, 0.15, 0.3, 0.5]:
    y,_ = resynth(8, 28.0, subgain=sg, seed=1)
    harmonics(y, 28.0, f'resynteza, sub={sg}')

print('\nPRZESTRAJANIE (czy da sie zmienic f0):')
for f0 in [24, 26, 28, 31, 34]:
    y,g = resynth(6, f0, subgain=0.3, seed=2)
    N = 1<<int(np.floor(np.log2(len(y))))
    S = np.abs(np.fft.rfft(y[:N]*np.hanning(N)))+1e-12
    cep = np.fft.irfft(np.log(S))
    lo,hi = int(SR/45), int(SR/18)
    q = lo+int(np.argmax(cep[lo:hi]))
    print(f'  cel {f0:>2} Hz -> zmierzone {SR/q:5.1f} Hz   ({g} ziaren)',
          '  OK' if abs(SR/q-f0) < 1.2 else '  ROZJAZD')

# render an audition file at 8k, then upsample for listening
y,_ = resynth(12, 28.0, subgain=0.3, seed=7)
pcm_out = (y*32767).astype('<i2')
with wave.open(P('data','test_resynth.wav'),'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(pcm_out.tobytes())
print('\nzapisano test_resynth.wav')
