# Handoff

Stan na moment przekazania. Dokument opisuje, co jest zrobione, dlaczego
podjęto takie decyzje i co zostało otwarte.

## Cel

Strona generująca dźwięki do stymulacji bilateralnej — mruczenie kota i deszcz
przesuwane między kanałami stereo. Ma brzmieć jak żywy kot, nie jak
syntezator, i nie może się zapętlać.

## Droga, którą przeszedł projekt

### v1 — synteza naiwna

Sinus 25 Hz z modulacją amplitudy 4,5 Hz, deszcz jako szum z kroplami
wyzwalanymi przez `setTimeout`. Brzmiało mechanicznie: brak chropowatości,
brak asymetrii wdech/wydech, słyszalne zapętlenie.

### v2 — synteza formantowa

- pociąg impulsów przez rezonator dwubiegunowy zamiast sinusa
- szum oddechowy przez **ten sam** rezonator i **tę samą** obwiednię, żeby
  siedział w tej samej przestrzeni akustycznej
- pregenerowane bufory pełnych cykli zamiast wyzwalania impulsów timerem
  (25 wywołań na sekundę dawałoby słyszalny jitter)
- rozdzielone osie kontroli: nastrój steruje f0 i tempem, odległość wyłącznie
  filtrem i poziomem. W v1 obie zmieniały jasność barwy i były nierozróżnialne.
- tło deszczu przestało być pannowane — pannowana przestrzeń brzmi jak
  przesuwający się pokój, nie jak deszcz

### v3 — model głosowy

Pięć ulepszeń, wszystkie mierzone offline harnessem w Node:

1. **Impuls Rosenberga** zamiast impulsu jednostkowego: narastanie pół-cosinus,
   opadanie ćwierć-cosinus, potem różniczkowanie dla asymetrycznego „ugryzienia"
2. **Bank 5 formantów równoległych** zamiast dwóch generycznych rezonansów:
   158 Hz (klatka piersiowa), 390, 830, 1650, 2950 Hz
3. **Shimmer** — nieregularność amplitudy z impulsu na impuls ±9%, obok
   istniejącego jitteru czasowego ±4%
4. **Kontur wysokości** wewnątrz fazy oddechowej: wzrost na początku, opadanie
   pod koniec
5. **Obwiednia `t·e^(−kt)`** zamiast sinusa, z podłogą 0,06 — kot nie milknie
   całkowicie między oddechami

**Błąd wykryty przez test:** zróżniczkowany impuls skaluje się jak 1/okres, więc
przy 25 Hz wychodził na amplitudzie 0,004, podczas gdy szum oddechowy miał 0,05.
Szum dominował dziesięciokrotnie — brzmiało to jak syczenie. Po normalizacji
impulsu liczba przejść przez zero spadła z 1414/s do 409/s.

Dodano też dwa suwaki panoramy: pozostałość w drugim kanale (skalowana przez
`acos` w tym, co faktycznie słychać) i charakter przejścia (waveshaper
`tanh(k·x)/tanh(k)`). Mapowanie `k` jest kwadratowe, bo liniowe nasycało się w
połowie suwaka i górna połowa nic nie robiła.

### v4 — ziarna z prawdziwego nagrania

Synteza z v3 została w całości zastąpiona resyntezą granularną. Szczegóły w
README. Najważniejsze ustalenie: skoki między ziarnami muszą trafiać w
**podobny kształt fali**, nie w losowe miejsce. Pomiar H4 przy trzech
strategiach:

| strategia | H4 |
|---|---|
| skoki losowe co 3–9 ziaren | −15,4 dB |
| skoki losowe co 8–20 ziaren | −16,0 dB |
| skoki dopasowane co 8–20 ziaren | **−12,0 dB** |
| materiał źródłowy | −7,4 dB |

### v5 — tagowanie ziaren

**Zadanie brzmiało: otagować ziarna fazą wdech/wydech. To się nie udało i nie
powinno być później próbowane w tej formie bez nowego nagrania.**

Pomiar: obwiednia całego nagrania, zawinięta na kandydujących częstotliwościach
modulacji, z estymatorem f0 opartym na autokorelacji w oknach 250 ms.

- W widmie modulacji dominuje 2,25 Hz (Welch, okna 16 s, rozdzielczość 0,06 Hz).
- Zawinięcie na 2,25 Hz daje **jeden** gładki garb, nie dwie fazy.
- Zawinięcie na 1,12 Hz, czyli przy założeniu dwóch impulsów na oddech, też
  daje jeden garb.
- f0 nie zależy od fazy: 27,0–28,3 Hz bez systematycznego związku, różnica
  między połówkami cyklu 0,37 Hz.

Wniosek: w tym materiale nie ma wykrywalnej naprzemienności wdech/wydech.
Częściowo to skutek doboru fragmentów — skan z v4 punktował stabilną strukturę
harmoniczną i karał transjenty, więc systematycznie omijał przejścia między
fazami. Żeby to naprawić, trzeba osobnego skanu nastawionego na przejścia, a
prawdopodobnie także nagrania z pełnym pasmem, bo faza wdechu jest cichsza i
najpewniej ginie pod progiem razem z obciętą podstawową.

**Pułapka pomiarowa po drodze:** pierwszy pomiar na samych fragmentach dał
„2,0–2,4 Hz" dla każdego z nich. Kolumna liczby cykli pokazywała same liczby
całkowite — detektor trafiał w kosze FFT, bo fragmenty mają 1,75–3,75 s, czyli
rozdzielczość 0,27–0,57 Hz. Modulację trzeba mierzyć na pełnym nagraniu.

Drugi: filtr pasmowy przy 1 Hz zaprojektowany na 48 kHz jest numerycznie
osobliwy (`LinAlgError: Singular matrix`). Obwiednię trzeba zdecymować przed
filtrowaniem tak wolnych modulacji.

**Co otagowano zamiast tego.** Zmierzono, co w ziarnach faktycznie się zmienia:

| cecha | rozrzut | korelacja z amplitudą |
|---|---|---|
| amplituda | 8,5× | — |
| jasność | 192× | −0,03 |
| centroid widma | 3,7× | −0,09 |
| f0 | 2,2× | −0,11 |

Amplituda i jasność są niezależne, więc dają dwie użyteczne osie. Obie zapisane
jako rangi percentylowe w tabeli epok. Szczegóły działania w README.

Zmiany w silniku dały: korelację poziomu z obwiedzią 0,91, powtarzalność
utrzymaną na 0,28 i czas regeneracji sześciu wariantów 34 ms (było 136 ms —
selekcja po tagach zawęża pulę, więc dopasowanie przebiegu liczy się szybciej).

**Regresja złapana po drodze:** samo dodanie selekcji po tagach podniosło
korelację między cyklami z 0,27 do 0,63. Cykle przy tych samych ustawieniach
szły niemal tą samą ścieżką przez bank. Naprawione losowym przesunięciem celów
na każdy cykl i poszerzeniem listy kandydatów z 10 do 16.

## Materiał źródłowy — co wiadomo

Nagrano dwa ujęcia telefonem.

**Ujęcie 1** (AAC 103 kb/s, 44,1 kHz): mediana poziomu −51,1 dBFS, H1 18,4 dB
pod H3. Nieużyteczne poza potwierdzeniem, że w ogóle jest tam mruczenie.

**Ujęcie 2** (PCM 32-bit, 88,2 kHz): mediana −29,7 dBFS, czyli 21 dB lepiej.
To ujęcie jest źródłem banku.

W obu **filtr górnoprzepustowy telefonu działał**, z narożnikiem około 26–28 Hz.
Widać to w zależności od f0 w danym fragmencie: przy f0 = 32,9 Hz H1 traci
8,7 dB, przy f0 = 27,0 Hz traci 18,2 dB. To wyklucza fizyczny rolloff
mikrofonu, który daje 6–12 dB/oktawę, nie kilkadziesiąt.

Analiza cepstralna daje rozstaw harmonicznych 28–33 Hz, zmienny między
fragmentami — to znak żywego zwierzęcia, nie artefaktu.

Skan całego nagrania oknem 1 s z krokiem 0,25 s wybrał 10 fragmentów, razem
24 s (16% materiału). Ocena składa się z wyrazistości harmonicznej (cepstrum),
przetrwania H1, poziomu i nachylenia widma, minus kara za transjenty.

**Uwaga o pierwszej próbie skanowania:** twarde progi na czterech metrykach
jednocześnie, każdy na poziomie mediany, dały jeden fragment na całe nagranie.
Ranking punktowy jest tu właściwym narzędziem, nie filtrowanie.

## Pułapka, na którą trzeba uważać przy edycji

`tools/04_assemble.py` wycina sekcję syntezy z szablonu i wstawia silnik
granularny. Znacznik końca to `function schedulePurr`, **nie** komentarz sekcji
deszczu. `schedulePurr` leży między `regeneratePurrCycles` a deszczem i cięcie
do komentarza deszczu usuwa go po cichu. Strona ładuje się wtedy bez błędu i
wywala `schedulePurr is not defined` dopiero przy pierwszym kliknięciu.

W skrypcie są asercje, które to teraz łapią. `tools/test_page.js` też.

## Co zostało otwarte

- **Podstawowa nadal syntetyczna.** Żeby ją nagrać, potrzebny mikrofon
  pojemnościowy z interfejsem USB, schodzący realnie do 20 Hz. Telefon tego nie
  zrobi niezależnie od ustawień aplikacji.
- **Rozmiar pliku.** 538 KB, z czego 500 KB to bank w base64. Jeśli to
  przeszkadza, alternatywą jest wydzielenie banku do osobnego pliku binarnego
  i pobieranie go przez `fetch` — kosztem tego, że strona przestanie działać z
  `file://`.
- **Faza wdechu.** Nie udało się jej wykryć w obecnym materiale (szczegóły
  wyżej). Wymaga nagrania z pełnym pasmem i skanu nastawionego na przejścia
  między fazami, a nie na stabilne odcinki.
- **Jasność przy niskim nastroju.** Sterowanie działa w górnej połowie zakresu;
  poniżej nastroju 0,5 pomiar jest niestabilny, bo wąskie okno dopasowania
  okresu wypycha wybór na ścieżkę fallbacku ignorującą okna tagów.
- **Deszcz nadal w pełni syntetyczny.** Ta sama technika granularna zadziałałaby
  na nagraniu deszczu, a deszcz jest dużo łatwiejszy do nagrania niż mruczenie —
  całe pasmo leży wysoko, więc filtr telefonu nie przeszkadza.
- **Brak zapisu ustawień.** Każde otwarcie strony startuje od wartości
  domyślnych.
