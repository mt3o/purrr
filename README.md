# Przechył — generator dźwięków bilateralnych

Strona, która składa mruczenie kota z ziaren prawdziwego nagrania i syntezuje
deszcz, a następnie przesuwa oba źródła między kanałami stereo w tempie
zbliżonym do stymulacji bilateralnej stosowanej w EMDR.

Wszystko dzieje się w przeglądarce, w Web Audio API. Nie ma backendu, nie ma
zależności, nie ma plików audio obok — `index.html` jest samowystarczalny.

**To narzędzie relaksacyjne, nie terapia.** Sama stymulacja bilateralna nie
zastępuje EMDR prowadzonego przez terapeutę; w protokole klinicznym jest tylko
jednym z elementów. Dowody na skuteczność samych dźwięków bilateralnych, w
oderwaniu od reszty procedury, są dużo słabsze niż dla pełnej terapii.

## Szybki start

Otwórz `index.html` w przeglądarce. Koniecznie na słuchawkach — bez nich
efekt przechyłu nie istnieje, a dolne pasmo mruczenia jest niesłyszalne na
głośnikach laptopa.

## Publikacja

Najkrócej:

```bash
./push.sh git@github.com:UZYTKOWNIK/przechyl.git
```

Skrypt inicjuje repo, robi commit i wypycha. Puste repozytorium musi już istnieć
po stronie serwera — albo, z zainstalowanym `gh`:

```bash
gh repo create przechyl --public --source=. --remote=origin --push
```

`index.html` to pojedynczy statyczny plik, więc zadziała wszędzie:

- **GitHub Pages** — wrzuć repo, w Settings → Pages wskaż gałąź. Plik
  `.nojekyll` jest już w repo, żeby Jekyll nie mieszał.
- **Netlify / Cloudflare Pages** — przeciągnij katalog, bez konfiguracji.
- **Własny hosting** — skopiuj sam `index.html`, nic więcej nie jest potrzebne.

Strona nie wymaga HTTPS ani serwera, ale Web Audio startuje dopiero po
interakcji użytkownika, co jest już obsłużone przyciskiem play.

## Sterowanie

| Suwak | Co robi |
|---|---|
| Kot ↔ Deszcz | miks obu źródeł, prawo równej mocy |
| Tempo przechyłu | częstotliwość LFO panoramy, 0,2–1,2 Hz |
| Pozostałość w drugim kanale | ile sygnału zostaje po przeciwnej stronie (0–70%) |
| Charakter przejścia | od gładkiego sinusa do niemal prostokątnego przerzutu |
| Głośność | poziom wyjściowy |
| Nastrój (kot) | f0 mruczenia i długość cyklu oddechowego |
| Odległość (kot) | filtr dolnoprzepustowy i poziom |
| Odtworzona podstawowa | ile syntetycznego basu dołożyć pod nagranie |
| Intensywność (deszcz) | gęstość kropli i barwa tła |

## Jak to działa

### Mruczenie — resynteza granularna

Bank ziaren pochodzi z 24 s prawdziwego mruczenia, wybranych automatycznie z
2,5-minutowego nagrania jako fragmenty o najczystszej strukturze harmonicznej.
Materiał przepróbkowano do 8 kHz (99,95% energii leży poniżej 4 kHz) i pocięto
na chwilach zwarcia głośni — 633 epoki, f0 w zakresie 25,6–34,0 Hz.

Odtwarzanie jest w stylu PSOLA: ziarno to dwa okresy w oknie Hanna,
wyśrodkowane na epoce, nakładane w tempie zadanym przez suwak nastroju. Ponieważ
ziarna kładzione są w tempie *docelowym*, a nie źródłowym, f0 da się przestrajać
bez zmiany barwy.

Playhead idzie sekwencyjnie przez nagranie, żeby przebieg był ciągły, a co 8–20
ziaren skacze do epoki o **podobnym kształcie fali** (iloczyn skalarny
znormalizowanych sygnatur jednookresowych). Losowe skoki rozbijały fazę górnych
harmonicznych — H4 spadało do −15,4 dB zamiast −12,0 dB przy dopasowaniu.

### Tagi ziaren

Każda epoka niesie dwie rangi percentylowe liczone po całym banku: **amplitudę**
i **jasność** (energia 200–2000 Hz do 20–200 Hz). Wyszły niezależne — korelacja
−0,03 — więc dają dwie osobne osie sterowania.

Obwiednia oddechowa nie jest już samym mnożnikiem głośności. Silnik dobiera
ziarna o amplitudzie pasującej do bieżącego miejsca w cyklu, a wzmocnienie
dokłada tylko resztę (`0,45 + 0,55·env`). Pełna obwiednia na dobranych ziarnach
modulowałaby podwójnie i brzmiała jak pompowanie. Zmierzona korelacja poziomu
renderu z obwiednią: 0,91.

Jasność jest sterowana suwakiem nastroju — zadowolony kot brzmi jaśniej, i to
jasnością nagrania, nie filtrem. Działa w górnej połowie zakresu (pięciokrotna
rozpiętość między nastrojem 0,5 a 1,0); przy najniższych ustawieniach pomiar
jest niestabilny, bo wąskie okno okresu wypycha wybór na fallback.

Cele obu tagów dostają losowe przesunięcie na każdy cykl. Bez tego cykle
budowane przy tych samych ustawieniach chodziły niemal identyczną ścieżką przez
bank i korelacja między nimi rosła z 0,27 do 0,63 — czyli tagowanie samo w sobie
przywracało słyszalną powtarzalność.

### Odtworzona podstawowa

Filtr górnoprzepustowy na wejściu mikrofonowym iPhone'a wyciął podstawową
mruczenia: H1 leżało 10–18 dB pod H3 w każdym ujęciu. Pod ziarna dokładany jest
więc sinus na f0, sterowany followerem obwiedni (atak 20 ms, zwolnienie 120 ms),
żeby oddychał razem z mruczeniem zamiast leżeć pod spodem jako dron.

To jedyna syntetyczna część mruczenia — i dokładnie ta, której mikrofon nie
mógł złapać.

### Deszcz — synteza

- tło: szum różowy z bufora 10 s, filtr pasmowy, szew wygaszony
- krople drobne: impulsy 15–40 ms, pasmo 2–6 kHz
- krople grube: impulsy 60–150 ms, pasmo 400–1200 Hz
- wspólna gęstość sterowana jednym suwakiem, z powolnym „oddychaniem" natężenia
- feedback delay 45 ms tylko na kroplach

### Panorama

Tło deszczu **nie jest** pannowane — inaczej brzmi jak przesuwający się pokój.
Przechylane są tylko krople i cały tor kota.

Suwak pozostałości jest skalowany w tym, co słychać, nie w surowej wartości
`pan`. StereoPanner używa prawa równej mocy, więc wartość przeliczana jest
wstecz przez `acos`: ustawienie 25% daje faktycznie 0,250 amplitudy w kanale
odległym.

## Struktura repo

```
index.html                     gotowa strona, samowystarczalna
data/
  bank_epochs.json             pozycje epok krtaniowych w banku
  bank_meta.json               f0 i regularność każdego fragmentu
  segments.json                fragmenty znalezione przez skan
source-audio/
  fragmenty/                   24 s wyciętego mruczenia (10 plików WAV)
tools/
  01_scan_segments.py          skan nagrania, progi twarde (historyczny)
  02_rank_segments.py          skan nagrania, ranking punktowy (używany)
  03_build_bank.py             detekcja epok, bank + base64
  04_assemble.py               wstrzyknięcie banku w szablon -> index.html
  page.template.html           szablon strony (wersja z syntezą)
  purr-engine.template.js      silnik granularny z placeholderami
  test_page.js                 harness: cały skrypt pod atrapami przeglądarki
  test_tags.js                 pomiar skutków tagowania ziaren
  test_resynth.py              weryfikacja DSP offline
  make_test_tone.py            generator tonów do sprawdzania mikrofonu
```

## Przebudowa banku

Wymaga `ffmpeg` oraz `numpy` i `scipy`.

```bash
python3 tools/03_build_bank.py     # fragmenty -> data/bank_*.json + base64
python3 tools/04_assemble.py       # szablon + bank -> index.html
node tools/test_page.js index.html # weryfikacja
```

Żeby wymienić materiał źródłowy na własny, wrzuć nagranie jako
`source-audio/nagranie.wav` i zacznij od `02_rank_segments.py`, który wybierze
użyteczne fragmenty. Skrypt wypisze je z pomiarami; wytnij je i podłóż do
`source-audio/fragmenty/`.

## Testy

`tools/test_page.js` uruchamia cały skrypt strony pod atrapami `AudioContext`,
`document` i `atob`, klika play, rusza każdym suwakiem, tickuje timery i
restartuje odtwarzanie. Sprawdzanie samej składni tego nie łapie — pierwsza
wersja v4 ładowała się bez błędu i wywalała dopiero przy kliknięciu.

```bash
node tools/test_page.js index.html
```

## Nagrywanie własnego materiału

Wnioski z tego, co już sprawdzone:

- iPhone stosuje filtr górnoprzepustowy i AGC na wejściu mikrofonowym. Dyktafon
  nie daje ich wyłączyć. Aplikacje używające `AVAudioSession` w trybie
  `.measurement` minimalizują przetwarzanie, ale nie gwarantują surowego strumienia.
- W przetestowanym nagraniu narożnik filtru siedział około 26–28 Hz, czyli
  dokładnie w paśmie podstawowej mruczenia. Im niżej mruczy kot, tym mocniej
  jest obcięty.
- Nagrywaj PCM, nie AAC. Mono — „stereo" z telefonu było zdublowanym mono.
- Celuj w szczyty około −12 dBFS. Pierwsze nagranie miało medianę −51 dBFS,
  co po normalizacji wyciąga szum kwantyzacji.
- Telefon oparty o coś stabilnego, nie trzymany — trzymanie daje transjenty,
  które w widmogramie widać jako gęste pionowe prążki.
- `tools/make_test_tone.py` generuje sekwencję tonów 20–400 Hz. Nagraj ją dwa
  razy, raz z przetwarzaniem włączonym i raz wyłączonym; różnica między
  nagraniami izoluje działanie DSP, bo charakterystyka głośnika i mikrofonu się
  skraca.

## Licencja

Kod: rób, co chcesz.

Nagranie mruczenia w `source-audio/` i wbudowane w `index.html` jest materiałem
autora repozytorium. Jeśli publikujesz fork z własnym nagraniem, pamiętaj, że
zastąpienie banku wymaga tylko przebudowy opisanej wyżej.
