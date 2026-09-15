# Dane pośrednie

- `bank_epochs.json` — pozycje epok krtaniowych i długości okresów w banku,
  w próbkach przy 8 kHz. To jest wbudowywane w `index.html`.
- `bank_meta.json` — f0 i regularność detekcji dla każdego fragmentu źródłowego.
- `segments.json`, `segments_merged.json` — fragmenty wybrane przez skan
  z pomiarami, na podstawie których je wycięto.

Pliki `bank_audio.npy`, `bank_b64.txt` i `*.wav` są generowane przez skrypty
i celowo pominięte w `.gitignore` — powstają na nowo przy przebudowie.
