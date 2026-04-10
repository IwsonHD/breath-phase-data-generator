# Breath Phase Data Generator

Aplikacja do nagrywania i etykietowania faz oddechu (inhale, exhale, silence) w czasie rzeczywistym.

Program zapisuje:
- audio WAV do folderu `raw`
- etykiety CSV do folderu `label`

Wszystkie najwazniejsze parametry sa konfigurowalne z poziomu UI:
- `PERSONNAME`
- `MODE` (`Nose` / `Mouth`)
- `MICROPHONEQUALITY` (`Good` / `Medium` / `Bad`)
- `MEANSOFUSAGE` (`Training` / `Evaluation`)
- katalog bazowy zapisu danych (Output folder)

## Wymagania

- Windows 10/11
- Python 3.10 lub 3.11 (zalecane)
- Mikrofon dzialajacy w systemie

## Instalacja krok po kroku (Windows, PowerShell)

1. Przejdz do folderu projektu:

```powershell
cd D:\projects\breath-phase-data-generator
```

2. Utworz i aktywuj wirtualne srodowisko:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Zaktualizuj narzedzia pip:

```powershell
python -m pip install --upgrade pip setuptools wheel
```

4. Zainstaluj zaleznosci:

```powershell
pip install -r requirements.txt
```

## Uruchomienie

```powershell
python breathing_recorder.py
```

Po starcie zobaczysz okno Pygame z formularzem konfiguracyjnym i przyciskami sterowania.

## Konfiguracja w UI

W gornym panelu ustawiasz:
- `PERSONNAME` - nazwa osoby, trafia do nazwy plikow
- `Output folder` - katalog bazowy, gdzie zapisane beda dane
- `MODE` - `Nose` albo `Mouth`
- `MICROPHONEQUALITY` - `Good`, `Medium`, `Bad`
- `MEANSOFUSAGE` - `Training` albo `Evaluation`

Mozesz wpisac sciezke recznie albo kliknac `Browse` i wybrac folder.

## Struktura zapisu danych

Dane sa zapisywane pod wybranym `Output folder`.

Dla `Training`:
- `<Output folder>/train/raw/*.wav`
- `<Output folder>/train/label/*.csv`

Dla `Evaluation`:
- `<Output folder>/eval/raw/*.wav`
- `<Output folder>/eval/label/*.csv`

## Sterowanie

- `START (SPACE)` - start nagrywania
- `STOP (S)` - stop nagrywania
- `QUIT (ESC)` - zamknij aplikacje
- `INHALE (W)` - ustaw etykiete inhale
- `EXHALE (E)` - ustaw etykiete exhale
- `SILENCE (R)` - ustaw etykiete silence

W trakcie nagrywania program zapisuje segmenty o stalej dlugosci:
- `Training`: 10 s
- `Evaluation`: 60 s

## Format plikow

### WAV
- mono
- 44.1 kHz
- 16-bit PCM

### CSV
Kazdy plik CSV zawiera:
- `class`
- `start_sample`
- `end_sample`

Wartosci probek odpowiadaja pozycjom w zapisanym pliku WAV.

## Ustawienie wejscia audio (INPUT_DEVICE_INDEX)

Aktualnie indeks urzadzenia wejsciowego jest ustawiony w kodzie:
- `INPUT_DEVICE_INDEX = 1` w pliku `breathing_recorder.py`

Przy starcie aplikacja wypisuje liste urzadzen audio w konsoli. Jezeli nagrywanie nie dziala, zmien `INPUT_DEVICE_INDEX` na poprawny numer urzadzenia.

## Troubleshooting

### Problem: instalacja `PyAudio` nie przechodzi

Sprobuj:

```powershell
pip install pipwin
pipwin install pyaudio
```

Nastepnie uruchom ponownie:

```powershell
pip install -r requirements.txt
```

### Problem: brak dzwieku / zle urzadzenie

- sprawdz liste urzadzen wypisana przy starcie
- ustaw poprawne `INPUT_DEVICE_INDEX` w kodzie
- upewnij sie, ze mikrofon ma uprawnienia systemowe

## Pliki w projekcie

- `breathing_recorder.py` - glowna aplikacja
- `requirements.txt` - zaleznosci Pythona
- `README.md` - instrukcja
