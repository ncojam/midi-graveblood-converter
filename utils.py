"""Общие утилиты и константы"""

NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

GM_DRUM_MAP = {
    27: "high_q", 28: "slap", 29: "scratch_push", 30: "scratch_pull",
    31: "sticks", 32: "square_click", 33: "metronome_click", 34: "metronome_bell",
    35: "acoustic_bass_drum", 36: "bass_drum_1", 37: "side_stick", 38: "acoustic_snare",
    39: "hand_clap", 40: "electric_snare", 41: "low_floor_tom", 42: "closed_hihat",
    43: "high_floor_tom", 44: "pedal_hihat", 45: "low_tom", 46: "open_hihat",
    47: "low_mid_tom", 48: "hi_mid_tom", 49: "crash_cymbal_1", 50: "high_tom",
    51: "ride_cymbal_1", 52: "chinese_cymbal", 53: "ride_bell", 54: "tambourine",
    55: "splash_cymbal", 56: "cowbell", 57: "crash_cymbal_2", 58: "vibraslap",
    59: "ride_cymbal_2", 60: "hi_bongo", 61: "low_bongo", 62: "mute_hi_conga",
    63: "open_hi_conga", 64: "low_conga", 65: "high_timbale", 66: "low_timbale",
    67: "high_agogo", 68: "low_agogo", 69: "cabasa", 70: "maracas",
    71: "short_whistle", 72: "long_whistle", 73: "short_guiro", 74: "long_guiro",
    75: "claves", 76: "hi_wood_block", 77: "low_wood_block", 78: "mute_cuica",
    79: "open_cuica", 80: "mute_triangle", 81: "open_triangle",
}

DRUM_PRIORITY = {
    'bass_drum_1': 100, 'acoustic_bass_drum': 99,
    'electric_snare': 90, 'acoustic_snare': 89, 'side_stick': 88,
    'hand_clap': 80,
    'closed_hihat': 70, 'pedal_hihat': 69, 'open_hihat': 68,
    'crash_cymbal_1': 60, 'crash_cymbal_2': 59, 'ride_cymbal_1': 58, 'ride_cymbal_2': 57,
    'hi_mid_tom': 50, 'low_mid_tom': 49, 'high_tom': 48, 'low_tom': 47,
    'high_floor_tom': 46, 'low_floor_tom': 45,
}

MARKER_TRACK_NAME = "Markers"

def note_name(midi_note):
    octave = (midi_note // 12) - 1
    name = NOTE_NAMES[midi_note % 12]
    return f"{name}{octave}"

def note_to_filename(instrument_name, midi_note):
    if instrument_name.startswith("Drums") or instrument_name.startswith("Drum"):
        return GM_DRUM_MAP.get(midi_note, f"drum_{midi_note}")
    inst_name = instrument_name.lower().replace(' ', '_').replace('-', '_')
    nn = note_name(midi_note).lower().replace('#', '_')
    return f"{inst_name}_{nn}"

def sanitize_enum(name):
    return name.upper().replace('.', '_').replace('-', '_')

def ticks_per_step_from_filename(filename):
    import re
    from pathlib import Path
    match = re.search(r'_(\d+)\.mid$', Path(filename).name)
    return int(match.group(1)) if match else 16