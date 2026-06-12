"""Обновление файлов проекта graveblood"""
import re
from pathlib import Path
from utils import sanitize_enum, note_to_filename, MARKER_TRACK_NAME

def update_res_tracker(builder, res_tracker_h, res_tracker_cpp, build_sounds_bat):
    """Обновляет res_tracker_sounds.h/.cpp и build_sounds.bat"""
    new_instruments = sorted(builder.all_instruments)
    
    existing_enums = set()
    if res_tracker_h.exists():
        content = res_tracker_h.read_text(encoding='utf-8')
        for match in re.finditer(r'^\s+(\w+),?\s*//', content, re.MULTILINE):
            existing_enums.add(match.group(1))
    
    truly_new = [inst for inst in new_instruments if inst not in existing_enums]
    
    if not truly_new:
        print("  ✓ Все инструменты уже есть в res_tracker_sounds.h")
        return
    
    print(f"  Новые инструменты для добавления: {len(truly_new)}")
    
    _update_res_tracker_h(truly_new, res_tracker_h)
    _update_res_tracker_cpp(truly_new, res_tracker_cpp)
    _update_build_sounds_bat(builder, truly_new, build_sounds_bat)


def _update_res_tracker_h(new_instruments, path):
    if not path.exists():
        return
    content = path.read_text(encoding='utf-8')
    existing = set()
    for match in re.finditer(r'^\s+(\w+),?\s*(?://|$)', content, re.MULTILINE):
        existing.add(match.group(1))
    truly_new = [inst for inst in new_instruments if inst not in existing]
    if not truly_new:
        print("  ✓ Все инструменты уже есть в res_tracker_sounds.h")
        return
    marker = "    TRK_SND_COUNT"
    new_lines = [f"    {inst}," for inst in sorted(truly_new, key=str.lower)]
    content = content.replace(marker, "\n".join(new_lines) + "\n" + marker)
    path.write_text(content, encoding='utf-8')
    print(f"  ✓ Добавлено {len(truly_new)} инструментов в res_tracker_sounds.h")


def _update_res_tracker_cpp(new_instruments, path):
    if not path.exists():
        return
    content = path.read_text(encoding='utf-8')
    existing = set()
    for match in re.finditer(r'TRK_LIB_ENTRY\((\w+)\)', content):
        existing.add(match.group(1))
    new_entries = []
    for inst in sorted(new_instruments, key=str.lower):
        filename = inst.lower()
        if filename not in existing:
            new_entries.append(f"    TRK_LIB_ENTRY({filename}),")
    if not new_entries:
        print("  ✓ Все TRK_LIB_ENTRY уже есть в res_tracker_sounds.cpp")
        return
    insert_text = "\n".join(new_entries) + "\n"
    content = content.replace("\n};", f"\n{insert_text}}};")
    path.write_text(content, encoding='utf-8')
    print(f"  ✓ Добавлено {len(new_entries)} TRK_LIB_ENTRY в res_tracker_sounds.cpp")


def _update_build_sounds_bat(builder, new_instruments, path):
    if not path.exists():
        return
    content = path.read_text(encoding='utf-8')
    existing_vars = set()
    for match in re.finditer(r'\+tracker_snd_bank\.inc\s+(\w+)', content):
        existing_vars.add(match.group(1))
    
    new_wav_lines = []
    for inst_name, notes in builder.parser.instruments.items():
        if inst_name == MARKER_TRACK_NAME:
            continue
        for midi_note in notes.keys():
            filename = note_to_filename(inst_name, midi_note)
            enum_name = sanitize_enum(filename)
            if enum_name in new_instruments and filename not in existing_vars:
                wav_path = f"..\\sounds\\for-music\\{filename}.wav"
                bat_line = f"..\\..\\wav2incl.exe {wav_path} +tracker_snd_bank.inc {filename}"
                new_wav_lines.append(bat_line)
                existing_vars.add(filename)
    
    if not new_wav_lines:
        print("  ✓ Все строки уже есть в build_sounds.bat")
        return
    
    lines = content.split('\n')
    insert_idx = None
    for i, line in enumerate(lines):
        if 'skate' in line.lower() and 'snd_skate_bank' in line:
            insert_idx = i
            break
    if insert_idx is None:
        insert_idx = len(lines) - 1
    
    lines.insert(insert_idx, "\n".join(new_wav_lines))
    path.write_text('\n'.join(lines))
    print(f"  ✓ Добавлено {len(new_wav_lines)} строк в build_sounds.bat")


def update_music_data(song_name, music_data_h, music_data_cpp):
    enum_name = f"MUSIC_TRACK_{song_name.upper()}"
    include_line = f'#include "track_{song_name.lower()}.h"'
    # Ищем реальное имя переменной в сгенерированном .h файле
    array_entry = f'&trackerSong_{song_name}'  # как в сгенерированном коде

    # Проверяем по префиксу, а не по точному совпадению
    if music_data_cpp.exists():
        content = music_data_cpp.read_text(encoding='utf-8')
        
        # Проверяем, есть ли уже любая запись для этого трека
        if f'&trackerSong_{song_name}' not in content and f'MUSIC_TRACK_{song_name.upper()}' not in content.split('&trackerSong_')[0] if len(content.split('&trackerSong_')) > 1 else True:
            # Добавляем include
            if include_line not in content:
                last_include = content.rfind('#include "ambient_forest.h"')
                if last_include > 0:
                    end_of_line = content.find('\n', last_include)
                    content = content[:end_of_line+1] + include_line + '\n' + content[end_of_line+1:]
            
            # Добавляем в массив
            tracks_start = content.find('const TrackerSong* musicTracks')
            if tracks_start > 0:
                tracks_end = content.find('\n};', tracks_start)
                if tracks_end > 0:
                    content = content[:tracks_end] + f'\n    {array_entry},\t// {enum_name}' + content[tracks_end:]
            
            music_data_cpp.write_text(content, encoding='utf-8')
            print(f"  ✓ {array_entry} в music_data.cpp")
        else:
            print(f"  ✓ {array_entry} уже есть в music_data.cpp")