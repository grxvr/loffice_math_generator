# vim:fileencoding=utf-8:foldmethod=indent

from dataclasses import dataclass
from typing import Self, Tuple, Union
from math import hypot

import svgwrite
from svgwrite import shapes, text, path

Real_Number = Union[int, float]

@dataclass
class Point:
  x: Real_Number
  y: Real_Number

  def __init__(self, arg1, arg2=None):
    if isinstance(arg1, Real_Number) and isinstance(arg2, Real_Number):
      self.x, self.y = arg1, arg2
    elif isinstance(arg1, complex) and arg2 is None:
      self.x, self.y = arg1.real, arg1.imag
    elif (
      isinstance(arg1, (tuple, list))
      and len(arg1) == 2
      and isinstance(arg1[0], Real_Number)
      and isinstance(arg1[1], Real_Number)
      and arg2 is None
    ):
      self.x, self.y = arg1
    elif isinstance(arg1, Point):
      self.x, self.y = arg1
    else:
      raise ValueError(f"Wrong arguments, expected {Union[Tuple[Real_Number, Real_Number], complex]}")

  def __truediv__(self, other): 
    if isinstance(other,Point): return Point(self.x / other.x, self.y / other.y)
    else: return Point(self.x/other, self.y/other)
  def __mul__(self, other): 
    if isinstance(other,Point): return Point(self.x * other.x, self.y * other.y)
    else: return Point(self.x*other, self.y*other)
  def __add__(self, other):  
    if isinstance(other,Point): return Point(self.x + other.x, self.y - other.y)
    else: return Point(self.x+other, self.y-other)
  def __sub__(self, other): 
    if isinstance(other,Point): return Point(self.x - other.x, self.y - other.y)
    else: return Point(self.x-other, self.y-other)

  def __abs__(self): return hypot(self.x, self.y)

  def __iter__(self):
    yield self.x
    yield self.y

  def norm(self,basis:Point):
    return type(self)(basis.x + self.x, basis.y - self.y)

  def to_tuple(self): return (self.x,self.y)

@dataclass
class Arrow:
  w:Real_Number
  h:Real_Number
  def __init__(self,h=20,w=20,fill:bool=True):
    self.w = w
    self.h = h
    self.fill = fill

XY = Union[Tuple[Real_Number, Real_Number], Point, complex]

class Dot(Point):
  def __init__(self, arg1, arg2=None, radius: Real_Number = 5, fill=True, color="black",stroke_width=1):
    super().__init__(arg1, arg2)
    self.radius = radius
    self.fill = fill
    self.color = color
    self.stroke_width = stroke_width

  def draw(self,dwg:VectorPlot,**extra):
    if self.fill: dwg.add(shapes.Circle(self.to_tuple(),self.radius,fill=self.color,**extra)) # type: ignore
    else: dwg.add(shapes.Circle(self.to_tuple(),self.radius,fill='none',stroke=self.color,stroke_width=self.stroke_width,**extra)) # type: ignore

class TwoPointElement:
  def __init__(self,
    end: XY | None,
    start: XY = Point(0, 0),
    color="black",
    width: Real_Number = 1,
    text: str = "",
  ) -> None:
    self.start = Point(start)
    self.end = Point(end)
    self.len = hypot(self.end.x - self.start.x, self.end.y - self.start.y)
    self.color = color
    self.width = width
    self.text = text
  def __str__(self) -> str:
    return f'start = {self.start}; end = {self.end}'

class Vector(TwoPointElement):
  def __init__(
    self,
    end: XY,
    start: XY = Point(0, 0),
    color="black",
    width: Real_Number = 5,
    arrow: Arrow | None = None,
    text: str = "",
  ) -> None:
    super().__init__(end, start, color, width)
    self.arrow = arrow

  def move_x(self,x):
    self.start.x += x
    self.end.x += x
    return self

  def move_y(self,y) -> Self:
    self.start.y -= y
    self.end.y -= y
    return self

  def __add__(self,other):
    if isinstance(other,Vector):
      if self.is_normal != other.is_normal:
        raise ValueError("not allowed math operations with norm and non norm points")
      res = Vector(
        self.end + other.end,
        self.start + other.start,
        other.color,
        self.width,
        self.arrow
      )
      res.is_normal = other.is_normal
      return res
    else:
      return Vector(
        self.start + other,
        self.end   + other,
        self.color,
        self.width,
        self.arrow
      )


  is_normal = False
  def norm(self, basis): 
    self.is_normal = True
    return Vector(self.start.norm(basis), self.end.norm(basis), self.color, self.width, self.arrow)

  def draw(self, dwg: VectorPlot):
    # basis vector
    bvec = self.end - self.start
#   print(self.__str__())
    if abs(bvec) == 0: return
    if self.arrow is None: dwg.add(shapes.Line(self.start.to_tuple(), self.end.to_tuple(), stroke=self.color, stroke_width=self.width))
    else:
      bvec /= abs(bvec)
      m = self.end - bvec * self.arrow.h
      nx = -bvec.y
      ny = bvec.x
      b = (m.x + nx * self.arrow.w * 0.5, m.y + ny * self.arrow.w * 0.5)
      c = (m.x - nx * self.arrow.w * 0.5, m.y - ny * self.arrow.w * 0.5)
      if not self.arrow.fill: dwg.add(dwg.polygon([self.end.to_tuple(), b, c], fill="none", stroke=self.color, stroke_width=self.width))
      else: dwg.add(dwg.polygon([self.end.to_tuple(), b, c], fill=self.color))
      dwg.add(shapes.Line(self.start, m, stroke=self.color, stroke_width=self.width))

class VectorPlot(svgwrite.Drawing):
  def __init__(self, filename="unnamed_vector_plot.svg", size=(800, 600), transparent=False, basis=(-1, 0), **extra):
    self.size = size
    super().__init__(filename, size, **extra)
    if not transparent: self.add(shapes.Rect((0, 0), size, fill="white"))
    basis = Point(basis)
    self.margin = hypot(*size) / 10
    if basis.x > 0: bx = size[0] - self.margin
    elif basis.x < 0: bx = self.margin
    else: bx = size[0] / 2
    if basis.y > 0: by = self.margin
    elif basis.y < 0: by = size[1] - self.margin
    else: by = size[1] / 2
    self.basis = Point(bx, by)

  def draw_text(self, s: str, pos, font_size=20, text_anchor="end", dominant_baseline="middle"):
    self.add(text.Text(s,
      pos.to_tuple() if isinstance(pos, Point) else pos,
      font_size=font_size,
      text_anchor=text_anchor,
      dominant_baseline=dominant_baseline,
    ))

  def draw_axsis(self, AXname="", AYname="", dAX=(0, 0), dAY=(0, 0), font_size=20, color="black", width=5, arrow=Arrow()) -> None:
    ax = Vector((self.size[0] - self.margin * 0.5, self.basis.y), (self.margin * 0.5, self.basis.y), color, width, arrow)
    ay = Vector((self.basis.x, self.margin * 0.5), (self.basis.x, self.size[1] - self.margin * 0.5), color, width, arrow)
    ax.draw(self)
    self.draw_text(AXname,
      Point(ax.end.x - ax.arrow.h + dAX[0] + len(AXname)*font_size/10, ax.end.y + ax.arrow.w - dAX[1]) + 0.1*self.margin, #type: ignore
      font_size=font_size,
    )
    ay.draw(self)
    self.draw_text(AYname,
      Point(ay.end.x + ay.arrow.h * 0.75 + dAY[0] + len(AYname) * font_size / 2, ay.end.y + ay.arrow.w * 0.5 - dAY[1]), # type: ignore
      font_size=font_size,
    )

  def draw_2p_vector(self, arg1:Vector|XY|None=None, arg2:XY|None=None) -> None: 
    if isinstance(arg1,Vector):
      vector = arg1.norm(self.basis)
      vector.draw(self)
    elif arg1 is not None and arg2 is not None:
      vector = Vector(Point(arg2),Point(arg1))
      vector.norm(self.basis)
      vector.draw(self)

  def draw_basis_vector(self,point:XY, color="black", width: Real_Number = 5, arrow:Arrow|None=None) -> None: 
    vector = Vector(Point(point).norm(self.basis), Point(0, 0).norm(self.basis), color, width, arrow)
    vector.draw(self)

__all__ = ["Dot", "Point", "Arrow", "Vector", "VectorPlot"]

if __name__ == "__main__":
  import subprocess, os
  from math import sin, cos, radians
  from colorama import Fore, Style

  output_dir = 'vecplot_test'
  if not os.path.exists(output_dir): 
    os.mkdir(output_dir)

  cmd_ffmpeg = ["ffmpeg", "-framerate", "120", "-y", "-i", f"{output_dir}/image%03d.svg", "-c:v", "libx264", "-loop", "0", "output.mp4"]
  cmd_mpv = ["mpv", "output.mp4", "--loop"]

  SIZE = 500
  CENTER = SIZE / 2
  r = SIZE / 2 * 0.75
  Cx,Cy = 20,-20
  for i in range(361):
    filename = f"{output_dir}/image{i:03d}.svg"
    vp = VectorPlot(filename, (SIZE, SIZE),basis=(0,0))
    for deg,color in zip(map(lambda x: radians(x+i),range(0,301,60)),['red','blue','green','cyan','magenta','yellow']): 
#     vp.add(shapes.Ellipse(vp.basis,(r+Cx,r+Cy),fill='none',stroke='black',stroke_width=1))
      p = Point((CENTER + (r+Cx) * sin(deg), CENTER + (r+Cy) * cos(deg)))
      Vector(p, Point(0,0), arrow=None, color=color).draw(vp)
      Vector(p, Point(SIZE,SIZE), arrow=None, color=color).draw(vp)
    vp.save()

    print(Fore.YELLOW + "Generated file: " + Fore.CYAN + filename)
  print(f"{Fore.WHITE}Connecting geterated files via ffmpeg:\n{Fore.GREEN}{' '.join(cmd_ffmpeg)}{Style.RESET_ALL}")

  if subprocess.run(cmd_ffmpeg, capture_output=True):
    print(f"Opening via mpv:\n{Fore.GREEN}{' '.join(cmd_mpv)}{Style.RESET_ALL}")
    subprocess.run(cmd_mpv)
