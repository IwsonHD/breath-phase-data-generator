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
- `MICROPHONE INPUT` (wybor urzadzenia wejscia audio)
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

## Build EXE (Windows)

Po zainstalowaniu zaleznosci mozesz zbudowac samodzielny plik `.exe`:

```powershell
.\build_exe.ps1
```

Domyslnie powstaje:
- `dist/BreathingRecorder.exe`

Plik `.exe` mozesz przekazac uzytkownikowi razem z instrukcja, ze aplikacja zapisuje dane do folderu `data` obok pliku wykonywalnego (lub do folderu wybranego w UI).

Dodatkowe opcje builda:

```powershell
# build katalogowy (bez --onefile)
.\build_exe.ps1 -OneFile:$false

# wlasna nazwa artefaktu
.\build_exe.ps1 -Name "BreathRecorderApp"
```

## Konfiguracja w UI

W gornym panelu ustawiasz:
- `PERSONNAME` - nazwa osoby, trafia do nazwy plikow
- `Output folder` - katalog bazowy, gdzie zapisane beda dane
- `MODE` - `Nose` albo `Mouth`
- `MICROPHONEQUALITY` - `Good`, `Medium`, `Bad`
- `MEANSOFUSAGE` - `Training` albo `Evaluation`
- `MICROPHONE INPUT` - wybierane strzalkami `<` i `>` (zmiana mozliwa, gdy nagrywanie jest zatrzymane)

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

Domyslnie aplikacja uzywa systemowego urzadzenia wejsciowego.

Mozesz tez wybrac mikrofon bezposrednio w UI (`MICROPHONE INPUT`).

Przy starcie aplikacja wypisuje liste urzadzen audio w konsoli. Jesli chcesz wymusic konkretne urzadzenie, ustaw zmienna srodowiskowa:

```powershell
$env:BREATH_INPUT_DEVICE_INDEX = "1"
python breathing_recorder.py
```

Wersja `.exe` dziala analogicznie (ustaw zmienna srodowiskowa przed uruchomieniem). Jesli podany indeks jest niepoprawny, aplikacja automatycznie wraca do urzadzenia domyslnego.

## Jak generowac jakosciowe dane

Aby dataset byl jak najbardziej przydatny do treningu modelu:

- Nagrajcie rozne style oddychania: spokojny oddech, szybszy oddech (hiperwentylacja), podwojne wdechy i podwojne wydechy. Im wiecej roznych wariantow, tym lepiej.
- Nagrywajcie tylko nosem (ustawcie `MODE` na `Nose`).
- Pilnujcie, zeby nie bylo szumow w tle (muzyka, rozmowy, TV, wentylator, ruch uliczny, klikanie klawiaturą).
- Zmieniajcie polozenie mikrofonu miedzy sesjami (odleglosc i kat), zeby dane byly bardziej roznorodne i odporne na rozne warunki.
- Po pierwszym nagraniu odsluchajcie probke i sprawdzcie, czy oddech jest wyraznie slyszalny.
- Jesli warunki nagrania sie zmieniaja, lepiej zrobic kilka krotszych sesji niz jedna bardzo dluga. (Training -> 10s/Evaluation -> 60s)

## Gdzie przesłać dane?
Po wygenerowaniu danych proszę umieścić folder eval oraz train zawierające wygenerowane dane na dysku w folderze nazwnym twoimi inicjalami lub Imieniem i pierwszą literą nazwiska
LINK DO GOOGLE DRIVE - https://drive.google.com/drive/folders/15zvUczjwN4TCYZtvBDbmleqLHeGICHtm?usp=sharing
DZIĘKUJEMY <3

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
- wybierz inne urzadzenie w sekcji `MICROPHONE INPUT` w UI
- ewentualnie ustaw `BREATH_INPUT_DEVICE_INDEX` przed uruchomieniem
- upewnij sie, ze mikrofon ma uprawnienia systemowe

## Pliki w projekcie

- `breathing_recorder.py` - glowna aplikacja
- `requirements.txt` - zaleznosci Pythona
- `README.md` - instrukcja
