"""Сборка паттернов"""
from utils import sanitize_enum, note_to_filename, DRUM_PRIORITY

MAX_CHANNELS = 3
DRUM_CHANNEL = 2

class PatternBuilder:
    def __init__(self, parser, ticks_per_step):
        self.parser = parser
        self.ticks_per_step = ticks_per_step
        self.patterns = []
        self.order_list = []
        self.pattern_hashes = {}
        self.all_instruments = set()

    def build(self):
        """Основной метод сборки — финальная версия"""
        markers = self.parser.markers
        if not markers:
            self._build_single_pattern()
            return
        
        patterns_data = []
        
        i = 0
        prev_tick_4_4 = self.ticks_per_step
        prev_tick_3_3 = None
        prev_is_triplet = False
        
        while i < len(markers):
            start, duration, note = markers[i]
            
            if note == 12:  # C1
                pat_start = start
                pat_end = start + duration
                tick_4_4 = None
                tick_3_3 = None
                is_triplet = False
                
                # Ищем B0/A#0 среди ВСЕХ маркеров, которые попадают в [pat_start, pat_end]
                for n_start, n_dur, n_note in markers:
                    if n_start < pat_start or n_start >= pat_end:
                        continue
                    if n_note == 11:  # B0
                        tick_4_4 = n_dur
                    elif n_note == 10:  # A#0
                        tick_3_3 = n_dur
                        is_triplet = True
                
                # Заполняем из предыдущего паттерна то, что не указано
                if tick_4_4 is None:
                    tick_4_4 = prev_tick_4_4
                if tick_3_3 is None:
                    tick_3_3 = prev_tick_3_3
                
                # Обновляем предыдущие значения
                prev_tick_4_4 = tick_4_4 if tick_4_4 else prev_tick_4_4
                prev_tick_3_3 = tick_3_3
                prev_is_triplet = is_triplet
                
                patterns_data.append((pat_start, pat_end, tick_4_4, tick_3_3, is_triplet))
                i += 1
            else:
                i += 1
        
        pattern_idx = 0
        default_tps = self.ticks_per_step
        
        for pat_start, pat_end, tick_4_4, tick_3_3, is_triplet in patterns_data:
            if is_triplet and tick_3_3 is not None and tick_4_4 is not None:
                if tick_3_3 < tick_4_4:
                    tps = int(default_tps * 3 / 4)
                else:
                    tps = default_tps
            else:
                tps = default_tps
            
            # ЕДИНСТВЕННОЕ вычисление pat_length
            pat_length = (pat_end - pat_start) // tps
            
            print(f"  Паттерн {pattern_idx}: time={pat_start}-{pat_end}, steps={pat_length}, tps={tps}")
            
            events = self._collect_events(pat_start, pat_end, pat_length, tps)
            h = self._hash_events(events)
            if h in self.pattern_hashes:
                self.order_list.append(self.pattern_hashes[h])
            else:
                self.patterns.append((events, pat_length, tps))
                self.pattern_hashes[h] = pattern_idx
                self.order_list.append(pattern_idx)
                pattern_idx += 1
        
        print(f"  Всего паттернов: {pattern_idx}, order list: {len(self.order_list)}")

    def _collect_events(self, start_time, end_time, pat_length, tps):
        step_ticks = tps
        steps = pat_length
        events = [[None, None, None] for _ in range(steps)]
        
        # Разделяем инструменты
        melodic = []
        drums = []
        for inst_name, notes in self.parser.instruments.items():
            is_drum = self.parser.is_drum.get(inst_name, False)
            if is_drum:
                drums.append((inst_name, notes))
            else:
                melodic.append((inst_name, notes))
        
        # СНАЧАЛА мелодические (занимают каналы 0 и 1)
        for inst_name, notes in melodic:
            self._place_notes(inst_name, notes, False, events, start_time, end_time, step_ticks, steps)
        
        # ПОТОМ ударные (канал 2, конфликты переносятся ТОЛЬКО в свободные ячейки 0/1)
        for inst_name, notes in drums:
            self._place_notes(inst_name, notes, True, events, start_time, end_time, step_ticks, steps)
        
        return events

    def _place_notes(self, inst_name, notes, is_drum, events, start_time, end_time, step_ticks, steps):
        """Размещает ноты одного инструмента в событиях"""
        for midi_note, note_list in notes.items():
            enum_name = sanitize_enum(note_to_filename(inst_name, midi_note))
            self.all_instruments.add(enum_name)
            
            for note_start, note_dur, velocity in note_list:
                if note_start + note_dur <= start_time or note_start >= end_time:
                    continue
                
                rel_start = note_start - start_time
                step_idx = int(rel_start / step_ticks)
                if step_idx < 0 or step_idx >= steps:
                    continue
                
                if is_drum:
                    if events[step_idx][DRUM_CHANNEL] is None:
                        ch = DRUM_CHANNEL
                    else:
                        # Конфликт на канале 2 — пробуем канал 1 (но не 0!)
                        if events[step_idx][1] is None:
                            ch = 1
                        else:
                            # Оба заняты — разрешаем по приоритету только на канале 2
                            ch = self._resolve_drum_conflict(events, step_idx, enum_name)
                else:
                    # Мелодические: канал 0 в приоритете, потом канал 1
                    if events[step_idx][0] is None:
                        ch = 0
                    elif events[step_idx][1] is None:
                        ch = 1
                    else:
                        continue  # Оба заняты — скипаем
                
                if ch is None:
                    continue
                
                ghost = self._check_ghost(rel_start, step_ticks, step_idx, note_start, start_time, note_dur, enum_name, events, ch)
                velocity_hex = min(int(velocity / 127.0 * 0x0100), 0x0100)
                events[step_idx][ch] = (1, enum_name, velocity_hex, ghost)

    def _resolve_drum_conflict(self, events, step_idx, new_drum):
        """Разрешает конфликт ударных по приоритету (только каналы 2 и 1)"""
        existing = events[step_idx][DRUM_CHANNEL]
        
        if existing is None:
            return DRUM_CHANNEL
        
        existing_name = existing[1].lower() if isinstance(existing[1], str) else ""
        new_priority = DRUM_PRIORITY.get(new_drum.lower(), 0)
        existing_priority = DRUM_PRIORITY.get(existing_name, 0)
        
        if new_priority > existing_priority:
            # Новый важнее — старый пытаемся в канал 1
            if events[step_idx][1] is None:
                events[step_idx][1] = existing
                return DRUM_CHANNEL
            # Канал 1 занят — старый теряется, новый занимает канал 2
            return DRUM_CHANNEL
        else:
            # Новый менее важный — пытаемся в канал 1
            if events[step_idx][1] is None:
                return 1
            # Не удалось — скипаем
            return None

    def _check_ghost(self, rel_start, step_ticks, step_idx, note_start, pat_start, note_dur, enum_name, events, ch):
        step_offset = rel_start % step_ticks
        mid_step = step_ticks // 2
        if step_offset >= mid_step - 1 and step_offset <= mid_step + 1:
            return enum_name
        return 0

    def _hash_events(self, events):
        flat = []
        for step in events:
            for ch in step:
                flat.append(str(ch[1]) if ch else '0')
        return hash(tuple(flat))

    def _build_single_pattern(self):
        pass