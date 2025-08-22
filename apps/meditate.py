import wasp
import time
import math

class MeditateApp:
    NAME = "Meditate"
    ICON = "app.meditate"  # placeholder; add a 32x32 icon in resources

    def __init__(self):
        self.settings = {
            "mode": "timed",
            "duration_s": 600,
            "anchor_interval_s": 120,
            "fade_style": "thin",
            "fade_duration_s": 60,
            "pattern": "none",
            "bead_target": 108
        }
        self.active = False
        self.start_ts = None
        self.end_ts = None
        self.phase = None
        self.next_anchor = None
        self.fade_start_ts = None
        self.bead_index = 0

    # wasp-os lifecycle
    def foreground(self):
        wasp.watch.display.mute(False)
        self._draw_home()

    def background(self):
        pass

    def _draw_home(self):
        d = wasp.watch.drawable
        d.fill()
        d.set_color(0xFFFF)
        d.string("Meditate", 10, 10)
        d.string("Start {}m".format(self.settings["duration_s"] // 60), 10, 40)
        # A simple button area
        # TODO: draw ring preview, last stats

    def tap(self, event):  # event=(x,y)
        x, y = event
        if not self.active:
            self._start_session()
        else:
            if self.settings["mode"] == "beads":
                self._advance_bead()
            self._redraw_status()

    def _start_session(self):
        self.active = True
        now = wasp.now()
        self.start_ts = now
        self.phase = "run"
        if self.settings["mode"] == "timed":
            self.end_ts = now + self.settings["duration_s"]
            self.next_anchor = now + self.settings["anchor_interval_s"]
        elif self.settings["mode"] == "beads":
            self.bead_index = 0
        wasp.system.request_event(wasp.Event.TICK)  # ensure tick delivery
        self._redraw_status()
        wasp.watch.display.sleep(3000)  # allow screen to time out

    def _enter_fade(self):
        self.phase = "fade"
        self.fade_start_ts = wasp.now()
        wasp.system.request_event(wasp.Event.TICK)

    def _finish(self):
        self.phase = "done"
        self.active = False
        wasp.watch.vibrator.pulse(120)  # completion pulse
        self._draw_done()

    def _advance_bead(self):
        self.bead_index += 1
        if self.bead_index in (self.settings["bead_target"]//2,):
            wasp.watch.vibrator.pulse(60)
        if self.bead_index >= self.settings["bead_target"]:
            self._enter_fade()

    def _redraw_status(self):
        d = wasp.watch.drawable
        d.fill()
        if self.settings["mode"] == "timed":
            now = wasp.now()
            remain = max(0, self.end_ts - now if self.end_ts else 0)
            mins = remain // 60
            secs = remain % 60
            d.string("{:02d}:{:02d}".format(mins, secs), 10, 10)
            # progress ring
            if self.end_ts:
                frac = (now - self.start_ts) / (self.end_ts - self.start_ts)
                self._draw_ring(frac)
        elif self.settings["mode"] == "beads":
            self._draw_beads()

    def _draw_ring(self, frac):
        d = wasp.watch.drawable
        cx, cy, r = 120//2, 120//2, 55
        # Simple arc approximation (just a chord fill or dots)
        steps = 60
        lit = int(frac * steps)
        for i in range(steps):
            ang = 2*math.pi * i/steps - math.pi/2
            x = int(cx + math.cos(ang)*r)
            y = int(cy + math.sin(ang)*r)
            if i <= lit:
                d.pixel(x,y,0x07E0)

    def _draw_beads(self):
        d = wasp.watch.drawable
        total = 36  # rendered beads
        completed = int(self.bead_index / self.settings["bead_target"] * total)
        cx, cy, r = 120//2, 120//2, 50
        for i in range(total):
            ang = 2*math.pi * i/total - math.pi/2
            x = int(cx + math.cos(ang)*r)
            y = int(cy + math.sin(ang)*r)
            color = 0xFFFF if i > completed else 0x07E0
            d.pixel(x,y,color)

    def _draw_done(self):
        d = wasp.watch.drawable
        d.fill()
        d.string("Complete", 10, 10)
        d.string("Tap to exit", 10, 40)

    def tick(self, ticks):
        if not self.active:
            return
        now = wasp.now()
        if self.settings["mode"] == "timed" and self.phase == "run":
            if now >= self.end_ts:
                if self.settings["fade_style"] != "none":
                    self._enter_fade()
                else:
                    self._finish()
                return
            if now >= self.next_anchor:
                wasp.watch.vibrator.pulse(30)
                self.next_anchor += self.settings["anchor_interval_s"]
        if self.phase == "fade":
            fade_elapsed = now - self.fade_start_ts
            fd = self.settings["fade_duration_s"]
            if fade_elapsed >= fd:
                self._finish()
                return
            # schedule thinning pulse
            # Example: pulse every base*(1+progress) seconds
            # (Left as a simple example; would need storing last pulse time)
        wasp.system.request_event(wasp.Event.TICK)
