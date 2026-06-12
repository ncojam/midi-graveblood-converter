"""Парсинг MIDI-файла"""
from collections import defaultdict
import mido
from utils import MARKER_TRACK_NAME

class MidiParser:
    def __init__(self, midi_path, ticks_per_step):
        self.mid = mido.MidiFile(midi_path)
        self.ticks_per_step = ticks_per_step
        self.ppq = self.mid.ticks_per_beat
        tempos = [mido.tempo2bpm(msg.tempo) for track in self.mid.tracks 
                  for msg in track if msg.type == 'set_tempo']
        self.tempo = int(sum(tempos) / len(tempos)) if tempos else 120
        self.seconds_per_midi_tick = 60.0 / self.tempo / self.ppq
        self.our_ticks_per_midi_tick = self.seconds_per_midi_tick * 64.0
        print(f"Темп: {self.tempo} BPM, PPQ: {self.ppq}")
        
        self.instruments = {}
        self.is_drum = {}
        self.markers = []
        self.song_length = 0
        self.programs = {}

    def parse(self):
        for track in self.mid.tracks:
            track_name = track.name if track.name else f"Unnamed_{id(track)}"
            if track_name == MARKER_TRACK_NAME:
                self._parse_markers(track)
            elif len(track) > 10:
                self._parse_notes(track, track_name)
        for inst in self.instruments.values():
            for note_list in inst.values():
                note_list.sort(key=lambda x: x[0])

    def _parse_markers(self, track):
        abs_time = 0
        note_on_time = {}
        for msg in track:
            abs_time += msg.time
            if msg.type == 'note_on' and msg.velocity > 0:
                note_on_time[msg.note] = int(abs_time * self.our_ticks_per_midi_tick)
            elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                if msg.note in note_on_time:
                    start = note_on_time[msg.note]
                    end = int(abs_time * self.our_ticks_per_midi_tick)
                    duration = max(end - start, 1)
                    self.markers.append((start, duration, msg.note))
                    del note_on_time[msg.note]
                    self.song_length = max(self.song_length, end)
        self.markers.sort(key=lambda x: x[0])

    def _parse_notes(self, track, track_name):
        is_drum = track_name.startswith("Drums") or track_name.startswith("Drum") or "drum" in track_name.lower()
        self.is_drum[track_name] = is_drum
        if track_name not in self.instruments:
            self.instruments[track_name] = defaultdict(list)
        inst = self.instruments[track_name]
        abs_time = 0
        note_ons = {}
        for msg in track:
            abs_time += msg.time
            if msg.type == 'program_change':
                self.programs[track_name] = msg.program
            elif msg.type == 'note_on' and msg.velocity > 0:
                note_ons[msg.note] = abs_time
            elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                if msg.note in note_ons:
                    start = int(note_ons[msg.note] * self.our_ticks_per_midi_tick)
                    end = int(abs_time * self.our_ticks_per_midi_tick)
                    duration = max(end - start, 1)
                    velocity = msg.velocity if msg.type == 'note_on' else 100
                    inst[msg.note].append((start, duration, velocity))
                    del note_ons[msg.note]
                    self.song_length = max(self.song_length, end)