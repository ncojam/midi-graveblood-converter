"""Генерация C++ кода трека"""
from pattern_builder import MAX_CHANNELS

def generate_track_code(song_name, builder):
    patterns = builder.patterns
    order_list = builder.order_list
    pat_lengths = sorted(set(p[1] for p in patterns))
    
    h_code = f"""// track_{song_name.lower()}.h
#ifndef TRACK_{song_name.upper()}_H
#define TRACK_{song_name.upper()}_H

#include "../tracker_music.h"

extern const TrackerSong trackerSong_{song_name};

#endif
"""
    
    cpp_code = f"""// track_{song_name.lower()}.cpp
#include "track_{song_name.lower()}.h"
#include "../res_tracker_sounds.h"

"""
    
    cpp_code += "// ======== ДЛИНЫ ПАТТЕРНОВ ========\n"
    for pl in pat_lengths:
        cpp_code += f"#define PATLEN_{pl} {pl}\n"
    cpp_code += "\n"
    
    for p_idx, (events, pat_len, tps) in enumerate(patterns):
        cpp_code += f"// ======== ПАТТЕРН {p_idx} ({pat_len} шагов, tps={tps}) ========\n"
        cpp_code += f"static const TrackerEvent pat{p_idx}_events[] = {{\n"
        
        for ch in range(MAX_CHANNELS):
            cpp_code += f"    // КАНАЛ {ch}\n"
            line_count = 0
            for step in range(pat_len):
                evt = events[step][ch] if step < len(events) and events[step][ch] else None
                if evt:
                    note, inst, vol, ghost = evt
                    cpp_code += f"    {{{note}, {inst}, 0x{vol:04X}, {ghost}}},"
                else:
                    cpp_code += f"    {{0, 0, 0x0000, 0}},"
                line_count += 1
                if line_count % 4 == 0:
                    cpp_code += "\n"
            if line_count % 4 != 0:
                cpp_code += "\n"
            cpp_code += "\n"
        
        cpp_code += "};\n\n"
    
    cpp_code += "// ======== МАССИВ ВСЕХ ПАТТЕРНОВ ========\n"
    cpp_code += "static const TrackerPattern allPatterns[] = {\n"
    for p_idx, (events, pat_len, tps) in enumerate(patterns):
        cpp_code += f"    {{ pat{p_idx}_events, PATLEN_{pat_len}, {tps} }},  // паттерн {p_idx}\n"
    cpp_code += "};\n\n"
    
    cpp_code += "// ======== ORDER LIST ========\n"
    cpp_code += "static const u8 orderList[] = {\n    "
    cpp_code += ", ".join(str(o) for o in order_list)
    cpp_code += "\n};\n\n"
    
    default_tps = patterns[0][2] if patterns else builder.ticks_per_step
    default_pat_len = patterns[0][1] if patterns else 16
    
    cpp_code += f"""// ======== СБОРКА ТРЕКА ========
const TrackerSong trackerSong_{song_name} = {{
    allPatterns,
    sizeof(allPatterns) / sizeof(allPatterns[0]),
    orderList,
    sizeof(orderList) / sizeof(orderList[0]),
    {default_pat_len},  // defaultPatternLength
    {default_tps},      // ticksPerStep
}};
"""
    
    return h_code, cpp_code