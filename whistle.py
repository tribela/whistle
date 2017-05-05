#!/usr/bin/env python
import subprocess
import audioop
import re
import time

import pyaudio
import requests

from numpy import mean, std
from numpy.fft import fft

session = requests.session()
session.headers.update({
    'User-Agent': 'whistle/0.0',
})


class PyAudioInput():

    def __init__(self):
        self.rate = 48000
        p = pyaudio.PyAudio()
        self.stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.rate,
            input=True,
            frames_per_buffer=1024)

    def read(self):
        data = self.stream.read(1024)
        samples = [audioop.getsample(data, 2, n)
                   for n in range(0, 1024)]
        return samples


class ConsoleOutput():

    def __init__(self):
        pass

    def trigger_note(self, target):
        print(target)


class NoteMapper():
    note_names = [
        'C', 'C#', 'D', 'D#', 'E',
        'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    note_scales = range(12)
    # note_names = [
    #     'C', 'D', 'E', 'F', 'G', 'A', 'B']
    # note_scales = [0, 2, 3, 5, 7, 8, 10]  # From A

    def __init__(self):
        self._note_to_midi = {}

        self._frequencies = []
        a = 440.0
        for octave in range(0, 10):
            for note in self.note_scales:
                i = (octave - 5) * 12 + note
                self._frequencies.append(a * 2 ** (i/12.0))

        self._frequencies = self._frequencies[3:]

    def frequency_to_note(self, target):
        if not target:
            return

        min_distance = None
        best_idx = None

        for n, frequency in enumerate(self._frequencies):
            distance = abs(frequency - target)
            f, t = frequency, target
            a, b = (f, t) if f < t else (t, f)
            distance = b / a
            if min_distance is None or distance < min_distance:
                min_distance = distance
                best_idx = n

        octave = best_idx // len(self.note_names)
        note = best_idx % len(self.note_names)
        return octave, self.note_names[note]
        # return "{}{}".format(self.note_names[note], octave)

    @classmethod
    def note_to_integer(cls, note):
        name, octave = re.match(r'(.+?)(\d+)', note).groups()
        return int(octave) * len(cls.note_names) + cls.note_names.index(name)


def get_spectrum(samples):
    result = fft(samples)
    return result[:int(len(result)/2)]


def get_peak_frequency(spectrum, rate):
    best = -1
    best_idx = 0
    for n in range(0, len(spectrum)):
        if abs(spectrum[n]) > best:
            best = abs(spectrum[n])
            best_idx = n

    peak_frequency = best_idx * rate / (len(spectrum) * 2)

    return peak_frequency, best


def get_peak_frequencies(spectrum, rate):
    best = sorted(
        range(len(spectrum)),
        key=lambda i: spectrum[i],
        reverse=True)[:3]
    return [(n * rate / (len(spectrum) * 2), spectrum[n]) for n in best]


def process_notes(notes):

    notes = list(map(NoteMapper.note_to_integer, notes))

    def simplify(diff):
        if diff < 0:
            return -1
        elif diff > 0:
            return 1
        return 0

    diffs = [
        simplify(notes[i] - notes[i-1])
        for i in range(1, len(notes))
    ]

    print(diffs)

    if diffs == [1, 0]:
        session.put('http://omega2.lan:8000/switch/0')
    elif diffs == [-1, 0]:
        session.delete('http://omega2.lan:8000/switch/0')


def process_note(note):
    if note == 'A5':
        session.delete('http://omega2.lan:8000/switch/0')
    elif note == 'C6':
        session.put('http://omega2.lan:8000/switch/0')


def main():
    input = PyAudioInput()
    mapper = NoteMapper()
    buffer = []
    notes = []
    last_time = time.time()
    last_time_note = time.time()

    gap = 0.1  # seconds

    def process_buffer(freq=None):
        # Check if need to process note
        if freq:
            l, r = buffer[-1], freq
            if l > r:
                l, r = r, l
            diff = r / l
        else:
            diff = 0

        mean_freq = mean(buffer)
        std_devi = std(buffer)
        err_rate = std_devi / mean_freq

        result = False
        # or diff > (2 ** (1/12))\
        if err_rate > 0.03 or now - last_time > gap:
            if len(buffer) > 10:
                result = True

                print(err_rate)
                # Append to notes
                octave, note = mapper.frequency_to_note(mean_freq)
                name = '{}{}'.format(note, octave)
                print(name)
                notes.append(name)
            buffer.clear()
        return result

    while True:
        samples = input.read()
        if not len(samples):
            continue

        spectrum = get_spectrum(samples)

        now = time.time()
        if max(samples) > 4000:
            peak_frequency, power = get_peak_frequency(spectrum, input.rate)
            if not peak_frequency:
                continue

            if not 750 <= peak_frequency <= 2000:
                continue

            if buffer:
                if process_buffer(peak_frequency):
                    last_time_note = now

            last_time = now
            buffer.append(peak_frequency)
        else:
            if now - last_time > gap and buffer:
                if process_buffer():
                    last_time_note = now

            if now - last_time_note > 1 and notes:
                print(notes)
                process_notes(notes)
                notes.clear()


if __name__ == '__main__':
    main()
