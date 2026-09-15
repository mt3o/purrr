import json, base64, re

import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def P(*a): return os.path.join(ROOT, *a)

html = open(P('tools','page.template.html')).read()
newpurr = open(P('tools','purr-engine.template.js')).read()
b64 = open(P('data','bank_b64.txt')).read().strip()
epochs = json.load(open(P('data','bank_epochs.json')))

# compact epoch table
ep_js = '[' + ','.join('[' + ','.join(str(v) for v in row) + ']' for row in epochs) + ']'
newpurr = newpurr.replace('__BANK_B64__', b64).replace('__BANK_EPOCHS__', ep_js)

# ---- 1. replace the synthetic purr block ----
# NOTE: the end marker is schedulePurr, NOT the Rain comment. schedulePurr
# sits between regeneratePurrCycles and the rain section, and slicing to the
# Rain comment silently deletes it — the page then loads fine and throws
# "schedulePurr is not defined" only on the first click.
start = html.index('  /* ---------------------------------------------------------------\n     Purr cycle synthesis  (v3)')
end   = html.index('  function schedulePurr(){')
html = html[:start] + newpurr + '\n' + html[end:]

assert 'function schedulePurr' in html, 'scheduler zniknal przy cieciu'
assert 'rosenbergPulse' not in html, 'stara synteza nie zostala usunieta'

# ---- 2. add the sub-bass slider to the Cat group ----
html = html.replace(
"""      <div class="control">
        <div class="control-label"><span>Odległość</span><span class="val" id="distVal">na kolanach</span></div>
        <input type="range" id="distSlider" min="0" max="100" value="25">
        <div class="ends"><span>blisko</span><span>daleko</span></div>
      </div>""",
"""      <div class="control">
        <div class="control-label"><span>Odległość</span><span class="val" id="distVal">na kolanach</span></div>
        <input type="range" id="distSlider" min="0" max="100" value="25">
        <div class="ends"><span>blisko</span><span>daleko</span></div>
      </div>

      <div class="control">
        <div class="control-label"><span>Odtworzona podstawowa</span><span class="val" id="subVal">20%</span></div>
        <input type="range" id="subSlider" min="0" max="60" value="20">
        <div class="ends"><span>tylko nagranie</span><span>pełna klatka</span></div>
      </div>""")

# ---- 3. register the new slider ----
html = html.replace(
"  const distSlider  = el('distSlider');",
"  const distSlider  = el('distSlider');\n  const subSlider   = el('subSlider');")

# ---- 4. wire it up ----
html = html.replace(
"""  const RAINS = ['mżawka','lekki deszcz','równy deszcz','rzęsisty','ulewa'];""",
"""  subSlider.addEventListener('input', () => {
    el('subVal').textContent = subSlider.value + '%';
  });
  subSlider.addEventListener('change', () => { if(ctx) regeneratePurrCycles(); });

  const RAINS = ['mżawka','lekki deszcz','równy deszcz','rzęsisty','ulewa'];""")

# ---- 5. decode the bank once, before the first cycle is built ----
html = html.replace(
"""    // pregenerate cycles, then start the schedulers
    regeneratePurrCycles();""",
"""    // decode the grain bank once, then pregenerate cycles
    if(!bank){ bank = decodeBank(); bankSig = buildSignatures(); }
    regeneratePurrCycles();""")

# ---- 6. update the page copy ----
html = html.replace(
"""    Dwa źródła syntezowane w czasie rzeczywistym — mruczenie modelowane jako
    impulsy krtaniowe w rezonatorze, deszcz jako warstwy kropli nad szumowym tłem.
    Nic się nie zapętla. Słuchaj na słuchawkach.""",
"""    Mruczenie składane na żywo z ziaren prawdziwego nagrania, cięte na
    impulsach krtaniowych; deszcz syntezowany jako warstwy kropli nad
    szumowym tłem. Nic się nie zapętla. Słuchaj na słuchawkach.""")

open(P('index.html'),'w').write(html)
print('rozmiar:', round(len(html)/1024,1), 'KB')
print('epok w tabeli:', len(epochs))
