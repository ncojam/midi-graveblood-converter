"""Экспорт WAV-файлов через fluidsynth + ffmpeg"""
import struct
import subprocess
from pathlib import Path
import mido
from utils import note_to_filename

SAMPLE_RATE = 16384
FLUIDSYNTH_PATH = r"D:\Tools\fluidsynth-v2.5.4-win10-x64-cpp11\bin\fluidsynth.exe"

def trim_wav_silence(wav_path, threshold=0.02):
    """Обрезает тишину в конце WAV-файла"""
    with open(wav_path, 'rb') as f:
        riff = f.read(4)
        if riff != b'RIFF':
            return
        f.read(4)
        wave = f.read(4)
        if wave != b'WAVE':
            return
        while True:
            chunk_id = f.read(4)
            chunk_size = struct.unpack('<I', f.read(4))[0]
            if chunk_id == b'fmt ':
                f.read(chunk_size)
            elif chunk_id == b'data':
                data_start = f.tell()
                data_size = chunk_size
                break
            else:
                f.read(chunk_size)
        f.seek(data_start)
        raw_data = f.read(data_size)
    
    max_val = 0
    samples = len(raw_data) // 2
    for i in range(samples):
        val = abs(struct.unpack_from('<h', raw_data, i * 2)[0])
        if val > max_val:
            max_val = val
    
    threshold_val = int(max_val * threshold)
    last_loud = samples - 1
    for i in range(samples - 1, -1, -1):
        val = abs(struct.unpack_from('<h', raw_data, i * 2)[0])
        if val > threshold_val:
            last_loud = i
            break
    
    tail_samples = int(SAMPLE_RATE * 0.05)
    new_end = min(last_loud + tail_samples, samples)
    
    if new_end < samples - 10:
        new_data_size = new_end * 2
        with open(wav_path, 'r+b') as f:
            f.seek(4)
            f.write(struct.pack('<I', data_start - 8 + new_data_size))
            f.seek(data_start - 4)
            f.write(struct.pack('<I', new_data_size))
            f.seek(data_start + new_data_size)
            f.truncate()
        print(f"    ✂ Обрезано {int((data_size - new_data_size) / 2)} семплов тишины")


def export_wav(instrument_name, midi_note, midi_path, output_dir, soundfont=None, program=0):
    """Экспортирует одну ноту в WAV 16384 Гц моно 16-bit"""
    filename = note_to_filename(instrument_name, midi_note)
    wav_path = output_dir / f"{filename}.wav"
    
    if wav_path.exists():
        trim_wav_silence(wav_path)
        return wav_path
    
    if not soundfont or not Path(soundfont).exists():
        print(f"  ⚠ Нет soundfont для {filename}, создаю заглушку")
        import wave
        wav_path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(wav_path), 'w') as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SAMPLE_RATE)
            for _ in range(SAMPLE_RATE // 2):
                w.writeframes(struct.pack('<h', 0))
        trim_wav_silence(wav_path)
        return wav_path
    
    tmp_mid = output_dir / "_temp_note.mid"
    tmp_wav = output_dir / "_temp_note_full.wav"
    
    mid = mido.MidiFile()
    track = mido.MidiTrack()
    mid.tracks.append(track)
    
    is_drum = instrument_name.startswith("Drums") or instrument_name.startswith("Drum") or "drum" in instrument_name.lower()
    channel = 9 if is_drum else 0
    
    if not is_drum:
        track.append(mido.Message('program_change', program=program, time=0, channel=channel))
    
    track.append(mido.Message('note_on', note=midi_note, velocity=100, time=0, channel=channel))
    track.append(mido.Message('note_off', note=midi_note, velocity=0, time=480, channel=channel))
    mid.save(tmp_mid)
    
    result = subprocess.run(
        [FLUIDSYNTH_PATH, '-n', '-i', '-g', '1.5', '-r', str(SAMPLE_RATE),
         '-F', str(tmp_wav), soundfont, str(tmp_mid)],
        capture_output=True, text=True
    )
    
    if not tmp_wav.exists():
        print(f"  ❌ fluidsynth не создал {tmp_wav}")
        print(f"  stderr: {result.stderr[:200]}")
        return None
    
    subprocess.run(
        ['ffmpeg', '-y', '-i', str(tmp_wav),
         '-ac', '1', '-ar', str(SAMPLE_RATE), '-sample_fmt', 's16', str(wav_path)],
        capture_output=True, text=True
    )
    
    tmp_mid.unlink(missing_ok=True)
    tmp_wav.unlink(missing_ok=True)
    
    if wav_path.exists():
        print(f"  ✓ {filename}.wav")
        return wav_path
    else:
        print(f"  ❌ Ошибка ffmpeg для {filename}")
        return None