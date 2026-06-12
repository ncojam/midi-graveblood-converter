#!/usr/bin/env python3
"""MIDI-to-GBA Tracker Converter — точка входа"""
import sys, os
from pathlib import Path

os.environ["PATH"] = r"C:\ffmpeg\bin;" + os.environ.get("PATH", "")
DEFAULT_SOUNDFONT = r"D:\Tools\soundfonts\FluidR3_GM.sf2"

from utils import ticks_per_step_from_filename, MARKER_TRACK_NAME
from midi_parser import MidiParser
from pattern_builder import PatternBuilder
from wav_exporter import export_wav
from code_generator import generate_track_code
from project_updater import update_res_tracker, update_music_data

GRAVEBLOOD_PATH = Path("../graveblood")
SOUNDS_PATH = GRAVEBLOOD_PATH / "sounds" / "for-music"
SRC_MUSIC_PATH = GRAVEBLOOD_PATH / "src" / "music"
BUILD_SOUNDS_BAT = GRAVEBLOOD_PATH / "build_sounds.bat"
RES_TRACKER_H = GRAVEBLOOD_PATH / "src" / "res_tracker_sounds.h"
RES_TRACKER_CPP = GRAVEBLOOD_PATH / "src" / "res_tracker_sounds.cpp"
MUSIC_DATA_H = SRC_MUSIC_PATH / "music_data.h"
MUSIC_DATA_CPP = SRC_MUSIC_PATH / "music_data.cpp"

def main():
    if len(sys.argv) < 2:
        print("Использование: python convert.py input/Metal_12.mid")
        sys.exit(1)
    
    midi_path = Path(sys.argv[1])
    if not midi_path.exists():
        print(f"❌ Файл не найден: {midi_path}")
        sys.exit(1)
    
    song_name = midi_path.stem.rsplit('_', 1)[0]
    tps = ticks_per_step_from_filename(midi_path.name)
    
    print(f"🎵 Конвертация: {song_name} (ticksPerStep={tps})")
    
    # Soundfont
    soundfont = os.environ.get('SOUNDFONT', None)
    if not soundfont and Path(DEFAULT_SOUNDFONT).exists():
        soundfont = DEFAULT_SOUNDFONT
    
    # Парсинг
    parser = MidiParser(midi_path, tps)
    parser.parse()
    print(f"   Инструментов: {len(parser.instruments)}, Маркеров: {len(parser.markers)}, Длина: {parser.song_length} тиков")
    
    # Сборка
    builder = PatternBuilder(parser, tps)
    builder.build()
    print(f"   Уникальных паттернов: {len(builder.patterns)}, Длина order list: {len(builder.order_list)}")
    
    # WAV
    SOUNDS_PATH.mkdir(parents=True, exist_ok=True)
    print(f"\n💾 Экспорт WAV в {SOUNDS_PATH}")
    for inst_name, notes in parser.instruments.items():
        if inst_name == MARKER_TRACK_NAME:
            continue
        for midi_note in notes.keys():
            export_wav(inst_name, midi_note, midi_path, SOUNDS_PATH, soundfont, parser.programs.get(inst_name, 0))
    
    # Код
    print(f"\n📝 Генерация кода...")
    h_code, cpp_code = generate_track_code(song_name, builder)
    SRC_MUSIC_PATH.mkdir(parents=True, exist_ok=True)
    (SRC_MUSIC_PATH / f"track_{song_name.lower()}.h").write_text(h_code, encoding='utf-8')
    (SRC_MUSIC_PATH / f"track_{song_name.lower()}.cpp").write_text(cpp_code, encoding='utf-8')
    
    # Проект
    print(f"\n🔧 Обновление проекта...")
    update_music_data(song_name, MUSIC_DATA_H, MUSIC_DATA_CPP)
    update_res_tracker(builder, RES_TRACKER_H, RES_TRACKER_CPP, BUILD_SOUNDS_BAT)
    
    print(f"\n🎉 Готово!")

if __name__ == "__main__":
    main()