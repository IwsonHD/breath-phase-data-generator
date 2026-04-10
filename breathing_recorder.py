import csv
import datetime
import os
import time
import wave
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import pyaudio
import pygame
import pygame.freetype

# ###########################################################
# AUDIO_CHUNK = 2205 -> exactly 50 ms at 44.1 kHz
# 200 chunks = 10.00 seconds (441_000 samples)
# 1200 chunks = 60 seconds (2_646_000 samples)
# ###########################################################
AUDIO_CHUNK = 2205
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
INPUT_DEVICE_INDEX = 1

TRAINING_RECORDING_DURATION = 10
EVAL_RECORDING_DURATION = 60

TRAINING_TARGET_SAMPLES = RATE * TRAINING_RECORDING_DURATION
EVAL_TARGET_SAMPLES = RATE * EVAL_RECORDING_DURATION


class NoseMouth(Enum):
    Nose = 0
    Mouth = 1


class MicrophoneQuality(Enum):
    Good = 0
    Medium = 1
    Bad = 2


class DataMeansOfUsage(Enum):
    Evaluation = 0
    Training = 1


@dataclass
class AppConfig:
    output_root: str
    nose_mouth_mode: NoseMouth
    microphone_quality: MicrophoneQuality
    person_name: str
    means_of_usage: DataMeansOfUsage

    def copy(self) -> "AppConfig":
        return AppConfig(
            output_root=self.output_root,
            nose_mouth_mode=self.nose_mouth_mode,
            microphone_quality=self.microphone_quality,
            person_name=self.person_name,
            means_of_usage=self.means_of_usage,
        )


class SharedAudioResource:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self._log_available_devices()
        self.stream = self.p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=AUDIO_CHUNK,
            input_device_index=INPUT_DEVICE_INDEX,
        )
        self.buffer = None
        self.read(AUDIO_CHUNK)

    def _log_available_devices(self):
        print("Available audio devices:")
        for i in range(self.p.get_device_count()):
            dev_info = self.p.get_device_info_by_index(i)
            print(f"Device {i}: {dev_info['name']}")
            print(f"  Max Input Channels: {dev_info['maxInputChannels']}")
            print(f"  Default Sample Rate: {dev_info['defaultSampleRate']}")

    def read(self, size: int):
        self.buffer = self.stream.read(size, exception_on_overflow=False)
        return self.buffer

    def close(self):
        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()


class BreathingRecorder:
    def __init__(self, audio: SharedAudioResource, config: AppConfig):
        self.audio = audio
        self.current_class = "silence"
        self.frames = []
        self.recording = False
        self.events = []
        self.current_sample = 0
        self.recording_start_time: Optional[float] = None
        self.ui_config = config.copy()
        self.active_config = config.copy()
        self.active_target_samples = self._target_samples_for(self.active_config.means_of_usage)

    @staticmethod
    def _target_samples_for(means_of_usage: DataMeansOfUsage) -> int:
        if means_of_usage is DataMeansOfUsage.Training:
            return TRAINING_TARGET_SAMPLES
        return EVAL_TARGET_SAMPLES

    @staticmethod
    def _sanitize_person_name(name: str) -> str:
        safe = "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in name.strip())
        return safe.strip("_") or "unknown_person"

    @staticmethod
    def _resolve_output_dirs(output_root: str, means_of_usage: DataMeansOfUsage):
        usage_folder = "train" if means_of_usage is DataMeansOfUsage.Training else "eval"
        data_dir = os.path.join(output_root, usage_folder)
        raw_dir = os.path.join(data_dir, "raw")
        csv_dir = os.path.join(data_dir, "label")
        os.makedirs(raw_dir, exist_ok=True)
        os.makedirs(csv_dir, exist_ok=True)
        return raw_dir, csv_dir

    def update_ui_config(self, config: AppConfig):
        self.ui_config = config.copy()

    def start_recording(self):
        if self.recording:
            return

        if not self.ui_config.output_root.strip():
            raise ValueError("Output folder cannot be empty.")
        if not self.ui_config.person_name.strip():
            raise ValueError("Person name cannot be empty.")

        self.active_config = self.ui_config.copy()
        self.active_target_samples = self._target_samples_for(self.active_config.means_of_usage)
        self._resolve_output_dirs(self.active_config.output_root, self.active_config.means_of_usage)

        self.recording = True
        self.frames = []
        self.events = [(self.current_class, 0)]
        self.current_sample = 0
        self.recording_start_time = time.time()
        print(f"Recording started. Current class: {self.current_class}")

    def change_class(self, new_class: str):
        if self.recording:
            self.events.append((new_class, self.current_sample))
            self.current_class = new_class
            print(f"Class changed to: {new_class} at sample {self.current_sample}")

    def record_chunk(self):
        if not self.recording:
            return

        chunk = self.audio.read(AUDIO_CHUNK)
        self.frames.append(chunk)
        self.current_sample += AUDIO_CHUNK

        if self.current_sample == self.active_target_samples:
            self.save_sequence()
            self.frames = []
            self.events = [(self.current_class, 0)]
            self.current_sample = 0
        elif self.current_sample > self.active_target_samples:
            print(
                f"WARNING: Overshot sample target {self.current_sample} > {self.active_target_samples}. Resetting segment."
            )
            self.frames = []
            self.events = [(self.current_class, 0)]
            self.current_sample = 0

    def save_sequence(self):
        if not self.recording or not self.frames:
            return

        nose_mouth_str = "nose" if self.active_config.nose_mouth_mode == NoseMouth.Nose else "mouth"
        mic_quality_str = self.active_config.microphone_quality.name.lower()
        person_name = self._sanitize_person_name(self.active_config.person_name)
        file_prefix = f"{person_name}_{nose_mouth_str}_{mic_quality_str}"
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        raw_dir, csv_dir = self._resolve_output_dirs(
            self.active_config.output_root, self.active_config.means_of_usage
        )
        wav_path = os.path.join(raw_dir, f"{file_prefix}_{timestamp}.wav")
        csv_path = os.path.join(csv_dir, f"{file_prefix}_{timestamp}.csv")

        with wave.open(wav_path, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(self.audio.p.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b"".join(self.frames))

        with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["class", "start_sample", "end_sample"])
            for i in range(len(self.events) - 1):
                cls, start = self.events[i]
                _, end = self.events[i + 1]
                writer.writerow([cls, start, end])
            last_cls, last_start = self.events[-1]
            writer.writerow([last_cls, last_start, self.current_sample])

        print(f"SAVED: {file_prefix}_{timestamp} ({self.current_sample} samples)")
        print(f"  Audio: {wav_path}")
        print(f"  Labels: {csv_path}")

    def stop_recording(self):
        if not self.recording:
            return

        self.save_sequence()
        self.recording = False
        print("Recording stopped.")


class TextInput:
    def __init__(self, x: int, y: int, w: int, h: int, label: str, text: str = ""):
        self.rect = pygame.Rect(x, y, w, h)
        self.label = label
        self.text = text
        self.active = False

    def handle_mouse_down(self, mouse_pos):
        self.active = self.rect.collidepoint(mouse_pos)

    def handle_key_down(self, event):
        if not self.active:
            return
        if event.key == pygame.K_BACKSPACE:
            self.text = self.text[:-1]
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE):
            self.active = False
        elif event.unicode and event.unicode.isprintable() and len(self.text) < 220:
            self.text += event.unicode

    def draw(self, screen, font, title_font):
        label_surface, _ = title_font.render(self.label, (230, 230, 230))
        screen.blit(label_surface, (self.rect.x, self.rect.y - 24))

        fill_color = (50, 70, 90) if self.active else (30, 40, 52)
        border_color = (120, 180, 255) if self.active else (100, 100, 100)
        pygame.draw.rect(screen, fill_color, self.rect, border_radius=6)
        pygame.draw.rect(screen, border_color, self.rect, 2, border_radius=6)

        text_surface, _ = font.render(self.text, (255, 255, 255))
        text_y = self.rect.y + (self.rect.height - text_surface.get_height()) // 2
        screen.blit(text_surface, (self.rect.x + 10, text_y))


def select_output_directory(current_dir: str) -> Optional[str]:
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        directory = filedialog.askdirectory(
            initialdir=current_dir if os.path.isdir(current_dir) else os.getcwd(),
            title="Select output directory",
        )
        root.destroy()
        if directory:
            return directory
        return None
    except Exception as exc:
        print(f"Could not open folder picker: {exc}")
        return None


def draw_button(screen, font, rect, text, selected=False, accent=False):
    if selected:
        fill = (32, 122, 89)
        border = (95, 220, 165)
    elif accent:
        fill = (65, 84, 128)
        border = (135, 165, 230)
    else:
        fill = (65, 65, 65)
        border = (180, 180, 180)

    pygame.draw.rect(screen, fill, rect, border_radius=8)
    pygame.draw.rect(screen, border, rect, 2, border_radius=8)

    text_surface, _ = font.render(text, (255, 255, 255))
    text_x = rect.x + (rect.width - text_surface.get_width()) // 2
    text_y = rect.y + (rect.height - text_surface.get_height()) // 2
    screen.blit(text_surface, (text_x, text_y))


def run_ui(recorder: BreathingRecorder):
    pygame.init()

    width, height = 1280, 760
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption("Breathing Recorder")

    font = pygame.freetype.SysFont(None, 24)
    title_font = pygame.freetype.SysFont(None, 30)
    class_font = pygame.freetype.SysFont(None, 64)
    clock = pygame.time.Clock()

    person_input = TextInput(40, 90, 420, 42, "PERSONNAME", recorder.ui_config.person_name)
    output_input = TextInput(40, 170, 980, 42, "Output folder", recorder.ui_config.output_root)

    browse_button = pygame.Rect(1040, 170, 200, 42)

    mode_buttons = {
        NoseMouth.Nose: pygame.Rect(40, 260, 170, 48),
        NoseMouth.Mouth: pygame.Rect(230, 260, 170, 48),
    }
    quality_buttons = {
        MicrophoneQuality.Good: pygame.Rect(40, 340, 170, 48),
        MicrophoneQuality.Medium: pygame.Rect(230, 340, 170, 48),
        MicrophoneQuality.Bad: pygame.Rect(420, 340, 170, 48),
    }
    usage_buttons = {
        DataMeansOfUsage.Training: pygame.Rect(40, 420, 170, 48),
        DataMeansOfUsage.Evaluation: pygame.Rect(230, 420, 170, 48),
    }

    controls = {
        "start": pygame.Rect(40, 690, 220, 48),
        "stop": pygame.Rect(280, 690, 220, 48),
        "quit": pygame.Rect(520, 690, 220, 48),
    }

    class_buttons = {
        "inhale": pygame.Rect(790, 620, 140, 54),
        "exhale": pygame.Rect(950, 620, 140, 54),
        "silence": pygame.Rect(1110, 620, 140, 54),
    }

    running = True
    message = ""

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                continue

            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = event.pos
                person_input.handle_mouse_down(mouse_pos)
                output_input.handle_mouse_down(mouse_pos)

                if browse_button.collidepoint(mouse_pos):
                    selected = select_output_directory(output_input.text)
                    if selected:
                        output_input.text = selected

                for mode, rect in mode_buttons.items():
                    if rect.collidepoint(mouse_pos):
                        recorder.ui_config.nose_mouth_mode = mode

                for quality, rect in quality_buttons.items():
                    if rect.collidepoint(mouse_pos):
                        recorder.ui_config.microphone_quality = quality

                for usage, rect in usage_buttons.items():
                    if rect.collidepoint(mouse_pos):
                        recorder.ui_config.means_of_usage = usage

                if controls["start"].collidepoint(mouse_pos) and not recorder.recording:
                    recorder.update_ui_config(
                        AppConfig(
                            output_root=output_input.text,
                            nose_mouth_mode=recorder.ui_config.nose_mouth_mode,
                            microphone_quality=recorder.ui_config.microphone_quality,
                            person_name=person_input.text,
                            means_of_usage=recorder.ui_config.means_of_usage,
                        )
                    )
                    try:
                        recorder.start_recording()
                        message = ""
                    except ValueError as exc:
                        message = str(exc)

                if controls["stop"].collidepoint(mouse_pos) and recorder.recording:
                    recorder.stop_recording()

                if controls["quit"].collidepoint(mouse_pos):
                    running = False

                for class_name, rect in class_buttons.items():
                    if rect.collidepoint(mouse_pos) and recorder.recording:
                        recorder.change_class(class_name)

            if event.type == pygame.KEYDOWN:
                person_input.handle_key_down(event)
                output_input.handle_key_down(event)

                text_editing = person_input.active or output_input.active
                if text_editing:
                    continue

                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE and not recorder.recording:
                    recorder.update_ui_config(
                        AppConfig(
                            output_root=output_input.text,
                            nose_mouth_mode=recorder.ui_config.nose_mouth_mode,
                            microphone_quality=recorder.ui_config.microphone_quality,
                            person_name=person_input.text,
                            means_of_usage=recorder.ui_config.means_of_usage,
                        )
                    )
                    try:
                        recorder.start_recording()
                        message = ""
                    except ValueError as exc:
                        message = str(exc)
                elif event.key == pygame.K_s and recorder.recording:
                    recorder.stop_recording()
                elif event.key == pygame.K_w and recorder.recording:
                    recorder.change_class("inhale")
                elif event.key == pygame.K_e and recorder.recording:
                    recorder.change_class("exhale")
                elif event.key == pygame.K_r and recorder.recording:
                    recorder.change_class("silence")

        if recorder.recording:
            recorder.record_chunk()

        screen.fill((17, 22, 29))

        title_surface, _ = title_font.render("Breathing Data Recorder", (255, 255, 255))
        screen.blit(title_surface, (40, 24))

        person_input.draw(screen, font, title_font)
        output_input.draw(screen, font, title_font)
        draw_button(screen, font, browse_button, "Browse", accent=True)

        mode_label, _ = title_font.render("MODE", (230, 230, 230))
        screen.blit(mode_label, (40, 232))
        for mode, rect in mode_buttons.items():
            draw_button(
                screen,
                font,
                rect,
                mode.name,
                selected=(recorder.ui_config.nose_mouth_mode is mode),
            )

        quality_label, _ = title_font.render("MICROPHONEQUALITY", (230, 230, 230))
        screen.blit(quality_label, (40, 312))
        for quality, rect in quality_buttons.items():
            draw_button(
                screen,
                font,
                rect,
                quality.name,
                selected=(recorder.ui_config.microphone_quality is quality),
            )

        usage_label, _ = title_font.render("MEANSOFUSAGE", (230, 230, 230))
        screen.blit(usage_label, (40, 392))
        for usage, rect in usage_buttons.items():
            draw_button(
                screen,
                font,
                rect,
                usage.name,
                selected=(recorder.ui_config.means_of_usage is usage),
            )

        draw_button(screen, font, controls["start"], "START (SPACE)", accent=True)
        draw_button(screen, font, controls["stop"], "STOP (S)")
        draw_button(screen, font, controls["quit"], "QUIT (ESC)")

        target_samples = (
            TRAINING_TARGET_SAMPLES
            if recorder.ui_config.means_of_usage is DataMeansOfUsage.Training
            else EVAL_TARGET_SAMPLES
        )
        target_seconds = target_samples / RATE

        if recorder.recording:
            elapsed = time.time() - (recorder.recording_start_time or time.time())
            remaining = max(recorder.active_target_samples - recorder.current_sample, 0) / RATE
            status_text = (
                f"RECORDING | Class: {recorder.current_class.upper()} | "
                f"Samples: {recorder.current_sample}/{recorder.active_target_samples} | "
                f"Elapsed: {elapsed:.1f}s | Remaining: {remaining:.1f}s"
            )
            status_color = (255, 85, 85)
        else:
            status_text = (
                f"READY | Target segment: {target_seconds:.0f}s ({target_samples} samples) | "
                "Press START (SPACE)"
            )
            status_color = (220, 220, 220)

        status_surface, _ = font.render(status_text, status_color)
        screen.blit(status_surface, (40, 500))

        if message:
            message_surface, _ = font.render(f"Error: {message}", (255, 120, 120))
            screen.blit(message_surface, (40, 535))

        if recorder.recording:
            class_surface, _ = class_font.render(recorder.current_class.upper(), (84, 224, 146))
            screen.blit(class_surface, (810, 540))

        draw_button(
            screen,
            font,
            class_buttons["inhale"],
            "INHALE (W)",
            selected=(recorder.current_class == "inhale" and recorder.recording),
        )
        draw_button(
            screen,
            font,
            class_buttons["exhale"],
            "EXHALE (E)",
            selected=(recorder.current_class == "exhale" and recorder.recording),
        )
        draw_button(
            screen,
            font,
            class_buttons["silence"],
            "SILENCE (R)",
            selected=(recorder.current_class == "silence" and recorder.recording),
        )

        help_text, _ = font.render(
            "Shortcuts: SPACE=start, S=stop, W/E/R=class, ESC=quit", (160, 168, 179)
        )
        screen.blit(help_text, (40, 650))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


def main():
    default_output_root = os.path.abspath("./data")
    initial_config = AppConfig(
        output_root=default_output_root,
        nose_mouth_mode=NoseMouth.Nose,
        microphone_quality=MicrophoneQuality.Medium,
        person_name="Kinga_M",
        means_of_usage=DataMeansOfUsage.Evaluation,
    )

    audio = SharedAudioResource()
    recorder = BreathingRecorder(audio, initial_config)

    try:
        run_ui(recorder)
    finally:
        if recorder.recording:
            recorder.stop_recording()
        audio.close()


if __name__ == "__main__":
    main()
