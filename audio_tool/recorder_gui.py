import os
import re
import time
import tkinter as tk
import wave
import winsound
from tkinter import messagebox
from tkinter import ttk

import numpy as np
import sounddevice as sd


APP_TITLE = "Wizard Sound Maker"
DEFAULT_SAMPLE_RATE = 44100
CHANNELS = 1
DTYPE = "int16"  # easy WAV writing


def _repo_dir() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _safe_name(name: str) -> str:
    name = name.strip()
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"[^A-Za-z0-9._-]", "", name)
    return name or "wizard"


def _ensure_wav_extension(filename: str) -> str:
    filename = filename.strip()
    if not filename.lower().endswith(".wav"):
        filename += ".wav"
    return filename


def _list_input_devices() -> list[dict]:
    devices: list[dict] = []
    try:
        for idx, d in enumerate(sd.query_devices()):
            if d.get("max_input_channels", 0) > 0:
                devices.append(
                    {
                        "index": idx,
                        "name": d.get("name", f"Device {idx}"),
                        "default_samplerate": d.get("default_samplerate"),
                    }
                )
    except Exception:
        return []
    return devices


class RecorderApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("560x320")
        self.root.resizable(False, False)

        self.devices = _list_input_devices()

        self.is_recording = False
        self.stream: sd.InputStream | None = None
        self.frames: list[np.ndarray] = []
        self.record_start_monotonic: float | None = None
        self.last_audio: np.ndarray | None = None
        self.last_samplerate: int | None = None
        self.last_saved_path: str | None = None

        self._build_ui()
        self._refresh_status("Ready")

        if not self.devices:
            messagebox.showwarning(
                "No input devices",
                "No microphone/input devices were found.\n\n"
                "If you do have a mic, check Windows privacy settings and try again.",
            )

    def _build_ui(self) -> None:
        pad = 10
        container = ttk.Frame(self.root, padding=pad)
        container.pack(fill="both", expand=True)

        title = ttk.Label(container, text="Wizard Sound Maker", font=("Segoe UI", 14, "bold"))
        title.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 4))

        subtitle = ttk.Label(
            container,
            text="Records a WAV for the website. Default output is wizard.wav next to wizard.html.",
            foreground="#666",
        )
        subtitle.grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 10))

        ttk.Label(container, text="Audio input:").grid(row=2, column=0, sticky="w")
        self.device_var = tk.StringVar(value=self._default_device_label())
        self.device_combo = ttk.Combobox(
            container,
            textvariable=self.device_var,
            values=[self._device_label(d) for d in self.devices] or ["(none)"],
            state="readonly" if self.devices else "disabled",
            width=48,
        )
        self.device_combo.grid(row=2, column=1, columnspan=2, sticky="w")

        ttk.Label(container, text="Output WAV name:").grid(row=3, column=0, sticky="w", pady=(10, 0))
        self.filename_var = tk.StringVar(value="wizard.wav")
        self.filename_entry = ttk.Entry(container, textvariable=self.filename_var, width=40)
        self.filename_entry.grid(row=3, column=1, columnspan=2, sticky="w", pady=(10, 0))

        self.overwrite_var = tk.BooleanVar(value=True)
        self.overwrite_check = ttk.Checkbutton(container, text="Overwrite if file exists", variable=self.overwrite_var)
        self.overwrite_check.grid(row=4, column=1, columnspan=2, sticky="w", pady=(8, 0))

        out_hint = ttk.Label(container, text=f"Saves to: {_repo_dir()}", foreground="#666")
        out_hint.grid(row=5, column=0, columnspan=3, sticky="w", pady=(6, 0))

        self.record_btn = ttk.Button(container, text="Record", command=self.on_record)
        self.stop_btn = ttk.Button(container, text="Stop & Save", command=self.on_stop, state="disabled")
        self.listen_btn = ttk.Button(container, text="Listen", command=self.on_listen, state="disabled")

        self.record_btn.grid(row=6, column=0, sticky="we", pady=(14, 0))
        self.stop_btn.grid(row=6, column=1, sticky="we", pady=(14, 0), padx=(8, 0))
        self.listen_btn.grid(row=6, column=2, sticky="we", pady=(14, 0), padx=(8, 0))

        self.status_var = tk.StringVar(value="")
        self.saved_var = tk.StringVar(value="")

        ttk.Separator(container).grid(row=7, column=0, columnspan=3, sticky="we", pady=14)

        ttk.Label(container, text="Status:").grid(row=8, column=0, sticky="nw")
        ttk.Label(container, textvariable=self.status_var, wraplength=470).grid(row=8, column=1, columnspan=2, sticky="w")

        ttk.Label(container, text="Last saved:").grid(row=9, column=0, sticky="nw", pady=(8, 0))
        ttk.Label(container, textvariable=self.saved_var, wraplength=470).grid(row=9, column=1, columnspan=2, sticky="w", pady=(8, 0))

        for col in range(3):
            container.grid_columnconfigure(col, weight=1)

    def _device_label(self, d: dict) -> str:
        return f"{d['index']}: {d['name']}"

    def _default_device_label(self) -> str:
        if not self.devices:
            return "(none)"
        try:
            default_in = sd.default.device[0]
            for d in self.devices:
                if d["index"] == default_in:
                    return self._device_label(d)
        except Exception:
            pass
        return self._device_label(self.devices[0])

    def _selected_device_index(self) -> int | None:
        if not self.devices:
            return None
        label = self.device_var.get().strip()
        m = re.match(r"^(\d+):", label)
        if not m:
            return self.devices[0]["index"]
        return int(m.group(1))

    def _refresh_status(self, text: str) -> None:
        self.status_var.set(text)

    def _set_saved(self, path: str) -> None:
        self.saved_var.set(path)

    def on_record(self) -> None:
        if self.is_recording:
            return
        device_index = self._selected_device_index()
        if device_index is None:
            messagebox.showerror("No device", "No audio input device is available.")
            return

        try:
            dev = sd.query_devices(device_index)
            sr = int(dev.get("default_samplerate") or DEFAULT_SAMPLE_RATE)
        except Exception:
            sr = DEFAULT_SAMPLE_RATE

        self.frames = []
        self.last_audio = None
        self.last_samplerate = sr
        self.last_saved_path = None
        self.record_start_monotonic = time.monotonic()

        def callback(indata, frames, time_info, status):
            self.frames.append(indata.copy())

        try:
            self.stream = sd.InputStream(
                samplerate=sr,
                channels=CHANNELS,
                dtype=DTYPE,
                device=device_index,
                callback=callback,
                blocksize=0,
            )
            self.stream.start()
        except Exception as e:
            messagebox.showerror("Record failed", f"Could not start recording:\n\n{e}")
            return

        self.is_recording = True
        self.record_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.listen_btn.configure(state="disabled")
        self._refresh_status("Recording…")

    def on_stop(self) -> None:
        if not self.is_recording:
            return

        try:
            if self.stream is not None:
                self.stream.stop()
                self.stream.close()
        except Exception:
            pass
        finally:
            self.stream = None

        self.is_recording = False
        self.record_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")

        if not self.frames:
            self._refresh_status("Stopped. No audio captured.")
            return

        audio = np.concatenate(self.frames, axis=0)
        self.last_audio = audio

        dur = 0.0
        if self.record_start_monotonic is not None:
            dur = max(0.0, time.monotonic() - self.record_start_monotonic)

        try:
            out_path = self._save_wav(audio, self.last_samplerate or DEFAULT_SAMPLE_RATE)
            self.last_saved_path = out_path
            self._set_saved(out_path)
            self.listen_btn.configure(state="normal")
            self._refresh_status(f"Saved WAV ({dur:.1f}s).")
        except Exception as e:
            self._refresh_status("Stopped. Save failed.")
            messagebox.showerror("Save failed", f"Could not write WAV:\n\n{e}")

    def _save_wav(self, audio: np.ndarray, samplerate: int) -> str:
        filename = _ensure_wav_extension(_safe_name(self.filename_var.get()))

        out_dir = _repo_dir()
        os.makedirs(out_dir, exist_ok=True)

        path = os.path.join(out_dir, filename)
        if os.path.exists(path) and not self.overwrite_var.get():
            base, ext = os.path.splitext(path)
            n = 2
            while True:
                candidate = f"{base}_{n}{ext}"
                if not os.path.exists(candidate):
                    path = candidate
                    break
                n += 1

        if audio.dtype != np.int16:
            audio = np.clip(audio, -32768, 32767).astype(np.int16)

        with wave.open(path, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)
            wf.setframerate(int(samplerate))
            wf.writeframes(audio.tobytes())

        return path

    def on_listen(self) -> None:
        if self.is_recording:
            return
        if not self.last_saved_path:
            return

        try:
            # Built-in Windows WAV playback (avoids sounddevice OutputStream/CFFI issues).
            winsound.PlaySound(self.last_saved_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            self._refresh_status("Playing…")
        except Exception as e:
            messagebox.showerror("Playback failed", str(e))


def main() -> None:
    root = tk.Tk()

    try:
        style = ttk.Style(root)
        if "vista" in style.theme_names():
            style.theme_use("vista")
    except Exception:
        pass

    RecorderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
