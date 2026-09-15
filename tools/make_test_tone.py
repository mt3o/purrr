import numpy as np, wave, struct

import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def P(*a): return os.path.join(ROOT, *a)

SR = 48000
FREQS = [20, 25, 31.5, 40, 50, 63, 80, 100, 125, 160, 200, 400]
STEP = 2.0          # seconds per tone
FADE = 0.05         # fade in/out per step, avoids clicks
AMP  = 0.5

def step_tone(f, dur):
    n = int(SR*dur)
    t = np.arange(n)/SR
    x = np.sin(2*np.pi*f*t) * AMP
    fn = int(SR*FADE)
    ramp = np.linspace(0, 1, fn)
    x[:fn] *= ramp
    x[-fn:] *= ramp[::-1]
    return x

# short marker blip before each tone so you can count steps in the waveform
def blip():
    n = int(SR*0.08)
    t = np.arange(n)/SR
    x = np.sin(2*np.pi*1000*t) * 0.25
    fn = int(SR*0.01)
    ramp = np.linspace(0,1,fn)
    x[:fn] *= ramp; x[-fn:] *= ramp[::-1]
    return np.concatenate([x, np.zeros(int(SR*0.25))])

parts = [np.zeros(int(SR*0.5))]
for f in FREQS:
    parts.append(blip())
    parts.append(step_tone(f, STEP))
    parts.append(np.zeros(int(SR*0.3)))

sig = np.concatenate(parts)
sig = np.clip(sig, -1, 1)
pcm = (sig * 32767).astype(np.int16)

with wave.open(P('data','test-tony-niskie.wav'), 'wb') as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())

dur = len(sig)/SR
print(f'zapisano: {dur:.1f}s, {len(FREQS)} tonow')
print('kolejnosc:', ', '.join(str(f) for f in FREQS), 'Hz')
