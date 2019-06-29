import requests
import curses
import pygame
import select
import sys

class instrument:
    def __init__(self, name, sample):
        self.name = name
        self.sample = sample

class sequence:
    def __init__(self, instrument, values):
        self.instrument = instrument        
        self.length = len(values)
        self.notes = values

class pattern:
    def __init__(self, name, length, tempo, tracks):
        self.name = name
        self.length = length
        self.tempo = tempo
        self.tracks = []        

        for track in tracks:
            self.tracks.append(sequence(track['instrument'], track['steps']))

class name_list():
    def __init__(self, main_win):
        self.list = self.query_names()
        self.max_y, self.max_x = main_win.getmaxyx()
        self.box = curses.newwin(len(self.list)+2, 12, 3, int(self.max_x/2)-30+2)
        self.current_selection = 0

    def query_names(self):
        names = requests.get("https://api.noopschallenge.com/drumbot/patterns").json()
        return names

    def move(self, direction):
        if direction == 'up':
            self.current_selection -= 1
            if self.current_selection < 0:
                self.current_selection = len(self.list) - 1
        elif direction == 'down':
            self.current_selection += 1
            if self.current_selection > len(self.list) - 1:
                self.current_selection = 0

    def get_current(self):
        for i, name in enumerate(self.list):
            if i == self.current_selection:
                return name["name"]

    def draw(self):
        self.box.box()
        for i, name in enumerate(self.list):
            if i == self.current_selection:
                self.box.addstr(i+1, 1, name["name"],curses.A_REVERSE)
            else:
                self.box.addstr(i+1, 1, name["name"])

        self.box.refresh()

class input_handler():
    def __init__(self, seq, name_list):
        self.key = False; 
        self.seq = seq
        self.name_list = name_list

    def check(self):
        self.key = self.get_key()

        if self.key == 'j':
            self.name_list.move('down') 
            self.seq.clear()
            self.seq.reset_pos()
        elif self.key == 'k':
            self.name_list.move('up') 
            self.seq.clear()
            self.seq.reset_pos()
        elif self.key == 'r':
            self.seq.reset_pos() 
        elif self.key == 'q':
            quit()
        elif self.key == ' ':
            self.seq.toggle_playing()

    def get_key(self):
        if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
            return sys.stdin.read(1)
        return False

class sequencer:
    def __init__(self, main_win):
        pygame.mixer.pre_init(44100, -16, 1, 512)
        pygame.mixer.init()
        pygame.init()        

        self.samples = {}
        self.playing = True
        self.pos = 0
        self.patterns = {}
        self.selection = ""
        self.time_passed = 0

        self.names = name_list(main_win)
        self.handler = input_handler(self, self.names)

        self.max_y, self.max_x = main_win.getmaxyx()

        self.main_win = main_win
        self.info_box = curses.newwin(5, 45, 3, int(self.max_x/2)-30+14)
        self.stdscr = curses.newwin(30, 70, 1, int(self.max_x/2)-30)
        self.seq_box = curses.newwin(7, 45, 8, int(self.max_x/2)-30+14)
         
        self.samples["cowbell"] = pygame.mixer.Sound('samples/cowbell.wav')
        self.samples["ride"] = pygame.mixer.Sound('samples/ride.wav')
        self.samples["hihat"] = pygame.mixer.Sound('samples/hihat.wav')
        self.samples["snare"] = pygame.mixer.Sound('samples/snare.wav')
        self.samples["clap"] = pygame.mixer.Sound('samples/clap.wav')
        self.samples["rim"] = pygame.mixer.Sound('samples/rim.wav')
        self.samples["kick"] = pygame.mixer.Sound('samples/kick.wav')

    def update(self):
        self.time_passed += 1
        self.handler.check()
        self.names.draw()
        self.selection = self.names.get_current()

        if self.playing == True:
            if self.selection not in self.patterns:
                pat = self.query_pattern(self.selection)
                if pat:
                    self.patterns[self.selection] = pattern(pat['name'], pat['stepCount'], pat['beatsPerMinute'], pat['tracks'])
            
            if self.time_passed >= (1/(self.patterns[self.selection].tempo/60))*15:
                self.trigger(self.selection)
                self.time_passed = 0

            self.draw_info(self.selection)

    def trigger(self, selection):
        self.draw(self.patterns[selection], self.pos)
        self.play(self.patterns[selection], self.pos)
                
        self.pos += 1
        if self.pos >= self.patterns[selection].length:
            self.pos = 0
    
    def start(self, selection, patterns):
       if selection not in patterns:
           pat = self.query_pattern(self.selection)
           if pat:
               patterns[selection] = pattern(pat['name'], pat['stepCount'], pat['beatsPerMinute'], pat['tracks'])
    
    def play(self, pattern, i):
       for track in pattern.tracks:
           if track.notes[i]:
               self.samples[track.instrument].play()

    def draw(self, pattern, i):
        self.seq_box.box()

        for pos, track in enumerate(pattern.tracks):
            sequence = ""

            for j, note in enumerate(track.notes):
                sequence += str(note) + " "
            
            for j, note in enumerate(track.notes):
                if i == j:
                    self.seq_box.addstr(1+pos, 9+(j*2), str(note))
                else: 
                    self.seq_box.addstr(1+pos, 9+(j*2), str(note) + " ", curses.A_REVERSE)
            
            self.seq_box.addstr(1+pos, 1, track.instrument, curses.A_REVERSE)

        self.seq_box.refresh()

    def draw_info(self, selection):
        self.info_box.box()
        self.stdscr.addstr(1, 19, "Samiser's Drumbot Player")
        self.main_win.refresh()

        self.info_box.addstr(1, 1, "name: " + self.patterns[selection].name)
        self.info_box.addstr(2, 1, "tempo: " + str(self.patterns[selection].tempo))
        self.info_box.addstr(3, 1, "length: " + str(self.patterns[selection].length))

        self.info_box.refresh()
        self.info_box.refresh()
        self.stdscr.refresh()

    def clear(self):
        self.seq_box.clear()
        self.info_box.clear()

    def reset_pos(self):
        self.pos = 0

    def toggle_playing(self):
        self.playing = not self.playing

    def query_pattern(self, name):
        info_url = "https://api.noopschallenge.com/drumbot/patterns/"
        info = requests.get(info_url + name).json()
    
        return info

def main(main_win):
    clock = pygame.time.Clock()

    curses.curs_set(0)
    curses.cbreak()

    seq = sequencer(main_win)

    while True:
        clock.tick(60)
        seq.update()

if __name__ == "__main__":
    curses.wrapper(main)
