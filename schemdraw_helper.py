from math import nan
from typing import Iterable, Optional
import os
import sys
import warnings
import schemdraw
import schemdraw.elements as elm
import schemdraw.util as util

class mySource(elm.Source):
  def __init__(self, *d, **kwargs):
    super().__init__(*d, **kwargs)
    self.segments.append(
      schemdraw.Segment([(0.15, 0), (0.9, 0)], arrow="->")
    )

class myInductor(elm.Element2Term):
  def __init__(self, n: int = 3, **kwargs):
    super().__init__(**kwargs)
    ind_w = 1 / n
    self.segments.append(schemdraw.Segment([(0, 0), (nan, nan), (1, 0)]))
    [self.segments.append
      (schemdraw.SegmentArc(((i * 2 + 1) * ind_w / 2, 0),
      theta1=0, theta2=180, width=ind_w, height=ind_w))
    for i in range(n)]

class Transformator(elm.Element2Term):
  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self.elmparams["drop"] = (2, 0)
    self.elmparams["lblloc"] = "bottom"
    self.segments.append(
      schemdraw.Segment(
        [(0, 0), (0, 0), (nan, nan), (2, 0), (2, 0)]
      )
    )
    self.segments.append(schemdraw.Segment([(0, 0), (0.2, 0)]))
    self.segments.append(schemdraw.Segment([(1.8, 0), (2, 0)]))
    self.segments.append(schemdraw.SegmentCircle((0.7, 0), 0.5))
    self.segments.append(schemdraw.SegmentCircle((1.3, 0), 0.5))
    self.elmparams["theta"] = 0

resheight = 0.5
reswidth = resheight*2 

class AVR(elm.Element2Term):
  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self.segments.append(
      schemdraw.Segment(
        [
          (0, 0),
          (0, resheight),
          (reswidth, resheight),
          (reswidth, -resheight),
          (0, -resheight),
          (0, 0),
          (nan, nan),
          (reswidth, 0),
        ]
      )
    )

class KZ(elm.Element):
  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self.anchors["start"] = (0, 0)
    self.anchors["center"] = (0, 0)
    self.anchors["end"] = (0, 0)
    self.elmparams["drop"] = (0, 0)
    self.elmparams['lblofst'] = (0, -.2)
    self.elmparams["theta"] = 0
    self.elmparams["zorder"] = 4
    self.elmparams["fill"] = None
    self.segments.append( schemdraw.Segment(([
      (0.25, 0.5),
      (-0.1, 0.1),
      (0.25, 0.25),
      (-0.4, -0.4),
    ]), arrow='>'))

def new__exit__(self, exc_type, exc_val, exc_tb):
  """Exit context manager - save to file and display"""
  if (self.output_dir_name is not None 
    and self.outfile is not None
  and self.output_dir_name + '/' not in self.outfile):
    if not os.path.exists(self.output_dir_name): os.mkdir(self.output_dir_name)
    self.outfile = self.output_dir_name + '/' + self.outfile
  if '--schemdraw-lazy' in sys.argv and os.path.exists(self.outfile):
    if '--debug' in sys.argv:print(f'image {self.outfile} already exsits!')
    return
  schemdraw.schemdraw.drawing_stack.push_element(None)
  schemdraw.schemdraw.drawing_stack.pop_drawing(self)

  if self.outfile is not None:
    self.save(self.outfile, self.transparent, self.dpi)
    if '--debug' in sys.argv:
      print(f'writed {self.outfile}')
  if not self.fig: self.draw(show=False)
  if self.show and not hasattr(self.canvas, "plot"):
    try: display(self.fig)  # pyright: ignore
    except NameError: self.fig.show()  # Not in Jupyter/IPython

def new__init__(self,
  canvas=None,
  file: Optional[str] = None,
  transparent: bool = False,
  dpi: int = 300,
  show: bool = False,
  output_dir_name:str='images',
  **kwargs
):
  self.outfile = file
  self.output_dir_name = output_dir_name
  self.transparent = transparent
  self.dpi = dpi
  self.canvas = canvas
  self.show = show
  self.elements = []
  self.anchors = {}

  if "backend" in kwargs:
    self.canvas = kwargs.pop("backend")
    warnings.warn(
      "Use of `backend` is deprecated. Use `canvas`.",
      DeprecationWarning,
      stacklevel=2,
    )

  self.dwgparams = schemdraw.schemdraw.schemdrawstyle.copy()
  self.dwgparams.update(kwargs)
  self.unit = kwargs.get("unit", schemdraw.schemdraw.schemdrawstyle.get("unit"))

  self._here = util.Point((0, 0))
  self._theta = 0
  self._state = []  # Push/Pop stack
  self._interactive = False
  self.fig = None

Drawing   = schemdraw.Drawing
Source    = mySource
Inductor  = myInductor
Resistor  = elm.ResistorIEC
Ground    = elm.Ground
Dot       = elm.Dot
Line      = elm.Line
Capacitor = elm.Capacitor

schemdraw.Drawing.__exit__ = new__exit__
schemdraw.Drawing.__init__ = new__init__  # type: ignore

sides_example = [{"$X_1$":Inductor},{"$X_2$":Inductor},{"$X_3$":Inductor}]
def triangle(d:Drawing,
  sides: None | list[dict] = None, # {Element:label}
  dot_labels: list[str] = ["1", "2", "3"],
  dot_locs=['T','T','T'],
  deg: float = 0,
  elem_len: float = 2,
  dots_type = [Dot, Dot, Dot]
) -> Iterable:
  if sides is None: raise ValueError
  dots = []
  ## відняти елементи, які є точками
  calc_dots_in_side = lambda side: sum(1 for v in side.values() if (v == Dot or v==KZ))
  elem_count = max(len(side)-calc_dots_in_side(side) for side in sides)
  side_len =  elem_count * elem_len
  for i,(side,th) in enumerate(zip(sides,[0+deg, 2*120+deg,120+deg])):
    dots += [dots_type[i]().label(dot_labels[i],loc=dot_locs[i]) if dots_type[i] is not None else Dot(radius=0).color('#FFFFFFFF')]
    for k,v in side.items(): 
      loc = None
      if isinstance(k,tuple):
        k,loc = k
      if v != Dot and v != KZ: v().length(side_len/(len(side)-calc_dots_in_side(side))).label(k,loc=loc).theta(th)
      else:        v().label(k)
  return dots

def star(d: Drawing,
  sides: None | list[dict] = None,
  dot_labels: list[str] = ["1", "2", "3"],
  deg: float = 30,
  elem_len: float = 2,
) -> Iterable:
  if sides is None: raise ValueError
  amplitude = max(len(elem) for elem in sides) * elem_len
  dots = []
  dots += [Dot().label(dot_labels[0], loc='R' if 140>deg>100 else 'T')]
  for k,v in sides[0].items():
    v().length(amplitude / len(sides[0])).label(k).theta(330+deg)
  center = Dot(open=True)

  for i, elem, th in zip(range(1,len(sides)), sides[1:], [30+deg,270+deg]):
    d.move_from(center.start)
    for k, v in elem.items():
      loc = None
      if isinstance(k,tuple):
        k,loc = k
      v().length(amplitude / len(elem)).label(k,loc=loc).theta(th)
    dots += [Dot().label(dot_labels[i],loc='L' if 320>th>240 else 'T')]
  return dots


__all__ = ["schemdraw","Source","Inductor","Resistor","Ground","Dot","Line","Drawing","triangle","star"]
if __name__ == "__main__":
  import matplotlib
  import matplotlib.pyplot
  matplotlib.use('Agg')
  for t in range(1,361):
    filename = f'kz_test/img{t}.png'
    with Drawing() as d:
      d.config(2,fontsize=10)
      Line()
      KZ(fill=False).label("$K_2$").theta(t)
      Line().right()
    d.save(filename,dpi=100)
    matplotlib.pyplot.close()
    print(f'generated',filename)

if __name__ == "__main__":
  from matplotlib import use
  use('Agg')
  with Drawing(file='test.png') as d:
    d.config(2,fontsize=10)

    start = util.Point(d.here)
    Line().right().label("Початок\n(генерація)")

    d1 = Dot()
    Resistor().label("$R_{екв}$")
    Inductor().label("$jX_{екв}$")
    d2 = Dot()

    Line().right().length(1.5)
    Dot(radius=0).label("Кінець\n(споживання)")
    d.push()
    Line().right().length(1.5)
    earth_x_end = util.Point(d.here).x
    d.pop()

    Resistor().label(" $R_{нав}$").down().length(1.5)
    Inductor().label("$jX_{нав}$").length(1.5)
    Dot(radius=0.05)
    Ground().right()

    for dot in [d1,d2]:
      d.move_from(dot.start)
      Capacitor().down().label(r"${\frac{Q_{c}}{2}}$",loc='B').length(3)
      Dot(radius=0.05)
      Ground().right()
    else: earth_y = util.Point(d.here).y

    d.move_from(start,0,earth_y,0)
    Line().length(earth_x_end).color('gray')
    d1x,d1y = d1.start
    d2x,d2y = d2.start
    Line(arrow='->').at((d1x+0.2,d1y-0.5)).to((d2x-0.2,d2y-0.5)).label('$P+jQ_{eff}$',loc='B')
  d.save('img.png',dpi=300)
