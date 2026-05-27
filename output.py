# vim:fileencoding=utf-8:foldmethod=indent

import re, sys, os, math, numbers, math, cmath
from enum import Enum
from dataclasses import dataclass
from typing import Any, Callable, Self
from numpy import ndarray

class MathParser:
  pretty_names = {'pi':'%pi'}
  var_and_val = []
  target_var = None
  vars_idx = []
  stored_scopes = []

  class T(Enum):
    NUM, VAR, FUNC, OP, LP, RP, LLP, LRP, EQ, COMMA, END = range(11)

  @dataclass
  class Token:
    type: Any
    value: Any = None
  FUNCS: dict[str, Callable] = {
    "abs":   lambda a: f"{{{{lline {a[0]} rline}}}}",
    "pow":   lambda a: f"{{{a[0]}}}^{{{a[1]}}}",
    "sqrt":  lambda a: f"sqrt {{{{ {a[0]} }}}}",
    "nroot":  lambda a: f"nroot {{{{ {a[1]} }}}} {{{{ {a[0]} }}}}",
    "exp":   lambda a: f"e ^ {{{{ {a[0]} }}}}",
    "log":   lambda a: (f"log_{{{{ {a[1]} }}}} {a[0]}" if len(a) > 1 else f"log {a[0]}"),
    "log2":  lambda a: f"log_{{{{ 2 }}}} {a[0]}",
    "log10": lambda a: f"log_{{{{ 10 }}}} {a[0]}",
    "sin":   lambda a: f"sin({a[0]})" if 'over' not in a[0] else f"sin {{{{ {a[0]} }}}}",
    "cos":   lambda a: f"cos({a[0]})",
    "tan":   lambda a: f"tan({a[0]})",
    "floor": lambda a: f"lfloor {a[0]} rfloor",
    "ceil":  lambda a: f"lceil {a[0]} rceil",
    "fabs":  lambda a: f"|{a[0]}|",
    "sum":   lambda a: f"sum from {{i=1}} to {{ {len(a)} }} {{{{ {a[0]} }}}}",
    "complex": lambda a: (
      f"{a[0]}"
        +f" + j{'(' if any([op in a[1] for op in ['-', '+', 'cdot', 'over']]) else ''}"
      +f"{a[1]}" 
        +f"{')' if any([op in a[1] for op in ['-', '+', 'cdot', 'over']]) else ''}"
    ),

  }

  def add_scope(self,scope,priority):
    self.stored_scopes.append((priority,scope))

  def __init__(self,g,d=3,eps=1e-6,cplxstyle=-1) -> None:
    self.add_scope(g,0)
    self.d = d
    self.eps = eps
    self.cplxstyle = cplxstyle

  def fmt(self, v, d) -> str:
    if type(v) == str: return v
    if isinstance(v, complex):
      def algb(v, d):
        real_exsists = abs(v.real) > self.eps
        imag_exsists = abs(v.imag) > self.eps
        return "{}{}{}".format(
          self.fmt(v.real, d) if real_exsists else '',
          (("+" if real_exsists else '') if v.imag >= 0 else "-") if imag_exsists else '',
          ('j'+self.fmt(abs(v.imag), d)) if imag_exsists else ''
        )
      def geom(v, d):
        deg = math.degrees(cmath.phase(v))
        return "{}e^{{{}j{}°}}".format(
          self.fmt(math.sqrt(v.real**2 + v.imag**2), d),
          "" if deg >= 0 else "-",
          self.fmt(abs(deg), d)
        )
      if self.cplxstyle > 0: return geom(v, d)
      elif self.cplxstyle < 0: return algb(v, d)
      else: return algb(v, d) + " = " + geom(v, d)
    if isinstance(v, (int, float, numbers.Real)):
      if v == 0: return '0'
      v = float(v)
      if abs(v) < self.eps: return '0'
      if abs(v) > self.eps**-1:
        before, after = "{:e}".format(v).rsplit("e")
        return "{}{}10^{{{{{}{}}}}}".format(
          self.fmt(float(before), d) if float(before) % 1 != 0 else '',
          " cdot " if float(before) % 1 != 0 else '',
          "" if v > 0 else "-",
          abs(int(after)),
        )
      res = f"{v:.{d}f}".replace(".", ",").rstrip("0")
      return res[:-1] if res[-1] == "," else res
    if isinstance(v,list):
      return '[' + '``'.join([self.fmt(list_value,d) for list_value in v]) + ']'
    if isinstance(v,ndarray):
      return self.fmt(v.tolist(),d)
    else: raise ValueError(f"Unknown type of format target{type(v)}")

  def tokenize(self, text: str) -> list["MathParser.Token"]:
    T = self.T
    regex = (
        r"(?P<NUM>\d+(?:\.\d+)?(?:[eE][+-]?\d+)?j?)"
        r"|(?P<LIT>[a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*)*)"
        r"|(?P<OP>\*\*|[+\-*/])"
        r"|(?P<LP>\()|(?P<RP>\))|(?P<EQ>=)|(?P<COMMA>,)|(?P<SKIP>\s+)"
    )
    raw = [(m.lastgroup, m.group()) for m in re.compile(regex).finditer(text) if m.lastgroup != "SKIP"]
    
    MAP={"NUM":T.NUM,"OP":T.OP,"LP":T.LP,"RP":T.RP,"LLP":T.LLP,"LRP":T.LRP,"EQ":T.EQ,"COMMA":T.COMMA}
    tokens = []
    expr_has_result = 'EQ' in [v[0] for v in raw]
    if expr_has_result:
      self.target_var = self.Token(T.VAR, raw[0][1])
      raw = raw[2:]
    else: 
      self.target_var = self.Token(T.VAR, raw[0][1])
      raw = raw[1:]
    for i, (kind, val) in enumerate(raw):
      assert kind
      if kind == "LIT":
        val = val.split(".")[-1]
        is_func = i + 1 < len(raw) and raw[i + 1][1].startswith("(")
        t = (T.FUNC if is_func else T.VAR)
        if not is_func: self.vars_idx.append(i)
        tokens.append(self.Token(t, val))
      elif kind == 'NUM':
        if 'j' not in val:
          val = float(val) 
        else:
          val = complex(''.join(str(t.value) for t in tokens[-2:]) + val)
          tokens = tokens[:-2]
        tokens.append(self.Token(MAP[kind], val))
      else: tokens.append(self.Token(MAP[kind], val))
    return tokens + [self.Token(T.END)]

  def parse(self, expr: str) -> str:
    self.toks, self.pos = self.tokenize(expr), 0
    res = self._expr()
    if self._peek().type != self.T.END:
      raise SyntaxError(f"Trailing tokens at pos {self.pos}")
    return res
  
  def formula(self,expr,units,onlynumbers,nonumbers,nobody,prefix) -> str:
    res_list = []
    names = []
    values = []
    body = self.parse(expr)
    if self.target_var is not None:
      result_var = self.val_by_name(self.target_var.value,append=False)
      assert isinstance(result_var,dict)
      result_var_name = "".join(result_var.keys())
      result_var_name = (prefix if prefix else '') + (
        self.pretty_names[result_var_name]
        if result_var_name in self.pretty_names
        else result_var_name
      )
      result_var_name = result_var_name.replace('__','^')
      if result_var_name.startswith('_'): result_var_name = None
      rv = list(result_var.values())[0]
      if isinstance(rv,complex):
        current_cplxstyle = self.cplxstyle
        self.cplxstyle = 0
        result_var_val = self.fmt(rv, self.d)
        self.cplxstyle = current_cplxstyle
      else:
        result_var_val = self.fmt(rv, self.d)
      if self.toks.count(self.Token(self.T.EQ,'=')) > 0:
        nonumbers = True
    for idx, elem in zip(self.vars_idx, self.var_and_val):
      for k,v in elem.items():
        name = self.pretty_names[k] if k in self.pretty_names else k
        name = name.replace('__','^')
        names.append(name)

        var = self.fmt(v,self.d)
        nt = self.toks[idx+1]
        pt = self.toks[idx-1]
        if isinstance(v,complex) and (nt.value in ['*','**'] or pt.value in ['*','**', '-']):
          if not((v.real > 0 and v.imag == 0) or (v.imag > 0 and v.real == 0)): 
            var = '(' + var + ')'
        if isinstance(v, (int,float)) and pt.type == self.T.OP:
          if v < 0: var = '(' + var + ')'
        values.append(var)
    for part in [
        None if not result_var_name else result_var_name, 
        None if onlynumbers == True or len(names) == 0 or nobody else body.format(*names), 
        None if len(values) == 0 or nobody or nonumbers or (len(names) == 1 and len(self.toks) == 2) else body.format(*values),
        result_var_val]:
      res_list.append(part) if part is not None else ...
    self._reset()
    return (' = '.join(res_list) + (f" {units}" if units else ''))

  def _reset(self):
    self.var_and_val.clear()
    self.vars_idx.clear()
    self.target_var = None

  def _peek(self): return self.toks[self.pos]

  def _eat(self, *types):
    t = self.toks[self.pos]
    assert t.type in types, f"Expected {types}, got {t}"
    self.pos += 1
    return t

  @staticmethod
  def _grp(s: str) -> str:
    # Preserve literal parens or wrap in grouping braces
    return s if (s.startswith("{{") or (s.startswith("(") and s.endswith(")"))) else f"{{{{ {s} }}}}"

  def _expr(self) -> str:
    left = self._add()
    if self._peek().type == self.T.EQ:
      self._eat(self.T.EQ)
      return f"{left} = {self._add()}"
    return left

  def _add(self) -> str:
    left = self._mul()
    while (self._peek().type == self.T.OP and self._peek().value in "+-"):
      op = self._eat(self.T.OP).value
      left = f"{left} {op} {self._mul()}"
    return left

  def _mul(self) -> str:
    left = self._pow()
    while (self._peek().type == self.T.OP and self._peek().value in ("*", "/")):
      op, right = self._eat(self.T.OP).value, self._pow()
      left = (f"{self._grp(left)} over {self._grp(right)}" 
        if op == "/" else f"{left} cdot {right}")
    return left

  def _pow(self) -> str:
    base = self._unary()
    if self._peek().type == self.T.OP and self._peek().value == "**":
      self._eat(self.T.OP)
      exp = self._unary()
      return f"{base}^{self._grp(exp)}"
    return base

  def _unary(self) -> str:
    if self._peek().type == self.T.OP and self._peek().value == "-":
      self._eat(self.T.OP)
      return f"-{self._primary()}"
    return self._primary()

  def val_by_name(self, name, append=True):
    if __name__ == "__main__": return
    for _,scope in sorted(self.stored_scopes,key=lambda tup:tup[0]):
      if name in scope.keys(): 
        if append: 
          self.var_and_val.append({
            name:[v for k, v in scope.items() if k == name][0]
          })
          return
        else: return {name:
          [v for k, v in scope.items() if k == name][0]
        }
    else: raise NameError(f"name: {name}:{type(name)} not in scope:\n{sorted(self.stored_scopes,key=lambda tup:tup[0])}")

  def add_pretty_names(self,pairs):
    self.pretty_names.update(pairs)

  def _wrap(self) -> str:
    start_pos = self.pos
    self._eat(self.T.LP)
    inner = self._add()
    self._eat(self.T.RP)
    prev_tok = self.toks[start_pos - 1] if start_pos > 0 else None
    next_tok = self._peek()
    needs_parens = False
    
    pt = prev_tok.type if prev_tok else None
    pv = prev_tok.value if prev_tok else None
    nt = next_tok.type
    nv = next_tok.value

    # {} ** | +
    if nt == self.T.OP and nv == "**": needs_parens = True
    # over {} | -
    elif pt == self.T.OP and pv == "/": needs_parens = False
    elif nt == self.T.OP and nv == "/":
      # * ({}...{}) / | +
      if pt == self.T.OP and pv == "*": needs_parens = False
      # any ({}...{}) / | -
      else: needs_parens = False
    elif nt == self.T.OP and nv == "*": 
      if inner.count('over') == 1: needs_parens = False
      else: needs_parens = True
    elif pt == self.T.OP and pv in ("*", "-"):
      if inner.count('over') == 1: needs_parens = False
      else: needs_parens = True
    elif self.T.COMMA in (nt, pt): needs_parens = True
    if needs_parens: return f"({inner})"
    return f"{{{{ {inner} }}}}"

  def _primary(self) -> str:
    T, tok = self.T, self._peek()
    if tok.type == T.NUM: 
      tok.value = self.fmt(tok.value, self.d)
      return self._eat(T.NUM).value
    if tok.type == T.VAR:
      self._eat(T.VAR)
      self.val_by_name(tok.value)
      return "{}"
    if tok.type == T.FUNC:
      name = self._eat(T.FUNC).value
      self._eat(T.LP)
      args = self._args()
      self._eat(T.RP)
      return (self.FUNCS[name](args)
        if name in self.FUNCS else f"{name}({', '.join(args)})"
      )
    if tok.type == T.LP:
      return self._wrap()  # Інтеграція нового методу _wrap
    if tok.type == T.LLP:
      self._eat(T.LLP)
      inner = self._add()
      self._eat(T.LRP)
      return f"({inner})"
    return ""

  def _args(self) -> list[str]:
    if self._peek().type == self.T.RP: return []
    args = [self._add()]
    while self._peek().type == self.T.COMMA:
      self._eat(self.T.COMMA)
      args.append(self._add())
    return args

class S(int,Enum):
  LEFT,RIGHT,BLOCK,CENTER = range(4)

class Output:
  images_count = 0
  tables_count = 0
  class LT(Enum):
    PARA,FORM,IMG,TAB,HEAD,DESC = range(6)

  @dataclass 
  class Line():
    type: Any
    value: Any = None
    style: Any = None

  lines = []
  def __init__(self,g,d=3,eps=1e-6,cplxstyle=-1,work_number=None) -> None:
    self.file = self.get_entry_script()
    self.parser = MathParser(g,d,eps,cplxstyle)
    self.work_number = work_number
    self.odf = LibreOffice() if '--odf' in sys.argv else None

  def get_entry_script(self) -> str | None:
    main = sys.modules.get("__main__")
    path = getattr(main, "__file__", None)
    if path is None:
      return None
    return os.path.abspath(path)

  def parse_file(self):
    def strip_quotes(text):
      if text.startswith(('"',"'")): text = text[1:]
      if text.endswith(('"',"'")): text = text[:-1]
      return text

    assert self.file
    file = open(self.file)
    skip = False
    lastline = ''
    for i,l in enumerate(file):
      l = l.strip('\n')
      # Заголовки <str> #@# h/head <!n>
      # Параграфи <str> #@# para/text <!n>
      # Формули <expr> #@# f/None <!units> <opt>
      # Зображення <path> #@# img <opt>
      # Таблиці <var/path> #@# tab <opt>
      # Опис <str> #@# desc <opt>
      # path : type<str>, None : type<''>
      if '#@#' in l and l.count('#') == 2:
        expr, args = l.split("#@#")
        args = args.strip().split(' ')
        expr = expr.strip()
        # TODO: стилі
        if args[0].lower() == 'skip' and args[1].lower() == 'begin': skip = True
        if args[0].lower() == 'skip' and args[1].lower() == 'end': skip = False
        if skip == True: continue
        match args[0]:
          case 'h' | 'head':
            n = 1
            for arg in args:
              if arg.startswith('!'): n = int(arg.strip('!'))
            self.lines.append(self.Line(self.LT.HEAD,strip_quotes(expr),n))
          case 'p' | 'para':
            if not expr.startswith(('"',"'")):
              text = self.parser.val_by_name(expr,False)
              assert isinstance(text,dict)
              text = list(text.values())[0]
              self.lines.append(self.Line(self.LT.PARA,text))
              continue
            self.lines.append(self.Line(self.LT.PARA,strip_quotes(expr)))
          case 'i' | 'img' :
            zoom = 1
            for arg in args:
              if arg.startswith('!'): zoom = float(arg.strip('!'))
            if expr.startswith(('"',"'")): filename = strip_quotes(expr)
            else: 
              filename = self.parser.val_by_name(expr,False)
              filename = [k for _,k in filename.items()][0]
            self.lines.append(self.Line(self.LT.IMG,filename,zoom))
          case 't' | 'tab' :
            table = self.parser.val_by_name(expr,False)
            self.lines.append(self.Line(self.LT.TAB,*list(table.values()) if table is not None else ['UNREACHABLE']))
          case 'd' | 'desc':
            text = strip_quotes(expr)
            if self.lines[-1].type == self.LT.IMG: 
              self.images_count += 1
              text = f'Рисунок {f"{self.work_number}." if self.work_number else ""}{self.images_count} – {text}'
              self.lines.append(self.Line(self.LT.DESC,text,'e'))
            elif self.lines[-1].type == self.LT.TAB:
              self.tables_count += 1
              text = f'Таблиця {f"{self.work_number}." if self.work_number else ""}{self.tables_count} – {text}'
              self.lines.insert(-1,self.Line(self.LT.DESC,text,'j'))
            else:
              print(f"\033[31;1m{self.file.split('/')[-1]}:{i}\033[0m description used without image/table line")
              print(i-1,'|',"\033[35;1m"+lastline+"\033[0m")
              print(i,'|',"\033[35;1m"+l+"\033[0m")
              self.lines.append(self.Line(self.LT.DESC,text))
          case 'f' | _:
            if expr:
              units = ''
              onlynumbers = False
              nobody = False
              nonumbers = False
              prefix = ''
              for arg in args:
                if arg.startswith('!'): units = arg.strip('!')
                if arg.startswith('@') and ':' in arg:
                  k,v = arg[1:].split(':')
                  match k:
                    case 'prefix': prefix = v
                    case _:
                      if k in self.parser.__dict__.keys():
                        try:
                          v = float(v)
                          if v == int(v): v = int(v)
                        except ValueError:
                          continue
                        self.parser.__dict__.update({k:v})
                      else: raise ValueError (f"Key {k} is not in parser")
                if arg.startswith('$'):
                  match arg[1:]:
                    case 'onlynumbers': onlynumbers = True
                    case 'nobody': nobody = True
                    case 'nonumbers': nonumbers = True
              self.lines.append(self.Line(self.LT.FORM,self.parser.formula(expr,units,onlynumbers,nonumbers,nobody,prefix)))
      if i>0: lastline = l
  
  def add_pretty_names(self,pairs): self.parser.add_pretty_names(pairs)

  def add_scope(self,scope,priority): self.parser.add_scope(scope,priority)

  def output(self):
    self.parse_file()
    if self.odf is None:
      for l in self.lines:
        if not isinstance(l.value, str): print(l.type,l.value); continue
        if l.type == self.LT.IMG:
          if '--noimage' in sys.argv: continue
          os.system(f'kitten icat --fit=both {l.value}')
        else:
          if '=' in l.value:
            formula = list(map(lambda s: s.strip(),l.value.split('=')))
            colored_formula = [f"\033[{color+31};1m"+value+"\033[0m" for color,value in enumerate(formula)]
            print(' = '.join(colored_formula))
          else: print(l.value)
    else:
      for l in self.lines:
        lastLT = l.type
        match l.type:
          case self.LT.FORM:
            self.odf.formula(l.value)
          case self.LT.HEAD:
            self.odf.header(l.value,l.style)
          case self.LT.PARA:
            self.odf.paragraph(l.value)
          case self.LT.IMG:
            self.odf.image(l.value,l.style)
          case self.LT.DESC:
            self.odf.desc(l.value,lastLT)
          case self.LT.TAB:
            self.odf.table(l.value)
      self.odf.fin()

class LibreOffice:
  import uno, time, psutil,subprocess
  from com.sun.star.text.TextContentAnchorType import AS_CHARACTER  # pyright: ignore
  from com.sun.star.beans import PropertyValue  # pyright: ignore
  from com.sun.star.beans import PropertyValue  # pyright: ignore
  from com.sun.star.style import LineSpacing  # pyright: ignore

  class ControlCharacter(int, Enum):
    PARAGRAPH_BREAK,LINE_BREAK,HARD_HYPHEN,SOFT_HYPHEN,HARD_SPACE,APPEND_PARAGRAPH = range(6)

  def __init__(self) -> None: 
    if not any(p.info["name"] == "soffice.bin" for p in self.psutil.process_iter(["name"])):
      self.subprocess.Popen(["soffice", "--accept=socket,host=localhost,port=2002;urp;"])
      self.time.sleep(5)
    local = self.uno.getComponentContext()
    resolver = local.ServiceManager.createInstanceWithContext(
      "com.sun.star.bridge.UnoUrlResolver", local
    )

    self.ctx = resolver.resolve(
      "uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext"
    )
    self.smgr = self.ctx.ServiceManager
    desktop = self.smgr.createInstanceWithContext(
      "com.sun.star.frame.Desktop", self.ctx
    )

    self.doc = desktop.loadComponentFromURL("private:factory/swriter", "_blank", 0, ())

    self.text = self.doc.Text
    self.cursor = self.text.createTextCursor()
    self.cursor.gotoEnd(False)
    self.cursor.CharHeight = 14
    self._init_common_style()

  def _init_common_style(self):
    para_styles = self.doc.getStyleFamilies().getByName("ParagraphStyles")
    for name in para_styles.getElementNames():
      style = para_styles.getByName(name)
      if getattr(style, "OutlineLevel", 0) == 0:
        self.common_style = name

  def __get_heading_style(self, n):
    para_styles = self.doc.getStyleFamilies().getByName("ParagraphStyles")
    for name in para_styles.getElementNames():
      style = para_styles.getByName(name)
      if getattr(style, "OutlineLevel", 0) == n:
        return name

  def __get_line_spacing(self, height, mode):
    ls = self.LineSpacing()
    ls.Mode = mode
    ls.Height = height
    return ls

  def header(self, s, n=1) -> Self:
    self.cursor.ParaStyleName = self.__get_heading_style(n)
    self.text.insertString(self.cursor, s, 0)
    self.cursor.ParaAdjust = S.BLOCK
    self.text.insertControlCharacter(
      self.cursor, self.ControlCharacter.PARAGRAPH_BREAK, False
    )
    return self

  def formula(self, s, para_break=True) -> Self:
    formula = self.doc.createInstance("com.sun.star.text.TextEmbeddedObject")
    formula.CLSID = "078B7ABA-54FC-457F-8551-6147e776a997"
    formula.AnchorType = self.AS_CHARACTER
    self.text.insertTextContent(self.cursor, formula, 0)
    self.cursor.ParaTopMargin = 100
    self.cursor.ParaBottomMargin = 200
    self.cursor.ParaLineSpacing = self.__get_line_spacing(115, 0)
    math = formula.getEmbeddedObject()
    math.Formula = s
    if para_break:
      self.text.insertControlCharacter(
        self.cursor, self.ControlCharacter.PARAGRAPH_BREAK, False
      )
    return self

  def image(self, filename, zoom=1) -> Self:
    graphic_provider = self.smgr.createInstanceWithContext(
      "com.sun.star.graphic.GraphicProvider", self.ctx
    )
    file_url = self.uno.systemPathToFileUrl(os.path.abspath(filename))
    props = (self.PropertyValue(Name="URL", Value=file_url),)
    graphic = graphic_provider.queryGraphic(props)

    image = self.doc.createInstance("com.sun.star.text.TextGraphicObject")
    image.AnchorType = self.AS_CHARACTER
    image.Graphic = graphic
    size = graphic.Size100thMM
    w, h = size.Width, size.Height
    if not (w > 0 and h > 0):
      size_px = graphic.SizePixel
      dpi = 96
      w = size_px.Width * 2540 / dpi
      h = size_px.Height * 2540 / dpi
    style = self.doc.StyleFamilies.getByName("PageStyles").getByName("Standard")
    page_width = style.Width
    left = style.LeftMargin
    right = style.RightMargin
    max_width = page_width - left - right

    if w > max_width:
      scale = max_width / w
      w = int(w * scale)
      h = int(h * scale)
    image.Width = w * zoom
    image.Height = h * zoom

    self.cursor.ParaTopMargin = 0
    self.cursor.ParaBottomMargin = 0
    self.cursor.ParaLineSpacing = self.__get_line_spacing(200, 1)
    self.cursor.ParaAdjust = S.CENTER
    self.text.insertTextContent(self.cursor, image, False)
    self.text.insertControlCharacter(
      self.cursor, self.ControlCharacter.PARAGRAPH_BREAK, False
    )
    return self
  
  def insert_formula_text(self,s:str):
    formula_token = "$"
    token_pos = 0
    for i, c in enumerate(s):
      if c != formula_token: continue
      token_pos += 1
    if token_pos % 2:
      raise ValueError("non even number of tokens %i" % (token_pos % 2))
    block = s.split(formula_token)
    for i, b in enumerate(block):
      if b == "": continue
      if not i % 2: self.text.insertString(self.cursor, b, 0)
      else: self.formula(b, False)
    self.text.insertControlCharacter(
      self.cursor, self.ControlCharacter.PARAGRAPH_BREAK, False
    )

  def desc(self, s: str, linetype):
    self.insert_formula_text(s)
    self.cursor.ParaTopMargin = 0 if linetype == 'image' else 200
    self.cursor.ParaBottomMargin = 200 if linetype == 'image' else 0
    self.cursor.ParaLineSpacing = self.__get_line_spacing(115, 0)

  def paragraph(self, s):
    self.insert_formula_text(s)
    self.cursor.ParaTopMargin = 100
    self.cursor.ParaBottomMargin = 200
    self.cursor.ParaLineSpacing = self.__get_line_spacing(115, 0)
    self.cursor.ParaAdjust = S.BLOCK

  def table(self, t):
    rows, cols = len(t), max(len(c) for c in t)
    tbl = self.doc.createInstance("com.sun.star.text.TextTable")
    tbl.initialize(rows, cols)
    self.text.insertTextContent(self.cursor, tbl, False)
    for r in range(rows):
      for c in range(cols):
        cell = tbl.getCellByName(chr(ord("A") + c) + str(r + 1))
        cell.setString(t[r][c])
        cell_cursor = cell.createTextCursor()
        cell_cursor.ParaStyleName = self.common_style
        cell_cursor.setPropertyValue("ParaAdjust", S.CENTER)
    tbl.RepeatHeadline = False
    tbl.HeaderRowCount = 0

  def allign(self, a):
    par_cursor = self.text.createTextCursorByRange(self.cursor)
    par_cursor = par_cursor.queryInterface(
      self.uno.getTypeByName("com.sun.star.text.XParagraphCursor")
    )
    if not par_cursor:
      return
    par_cursor.gotoEndOfParagraph(False)
    if par_cursor.gotoPreviousParagraph(False):
      par_cursor.gotoStartOfParagraph(False)
    match a:
      case "e" | S.CENTER:
        par_cursor.setPropertyValue("ParaAdjust", S.CENTER)
      case "r" | S.RIGHT:
        par_cursor.setPropertyValue("ParaAdjust", S.RIGHT)
      case "l" | S.LEFT:
        par_cursor.setPropertyValue("ParaAdjust", S.LEFT)
      case "j" | S.BLOCK:
        par_cursor.setPropertyValue("ParaAdjust", S.LEFT)
      case _:
        print("не вийшло застосувати вирівнювання")

  def fin(self):
    props = (
      self.PropertyValue(Name="FilterName", Value="writer8"),
      self.PropertyValue(Name="Overwrite", Value=True),
    )
    self.doc.storeAsURL("file:///tmp/current.odf", props)
