Made by student for students

# Usage
```python
import random
from output import Output, MathParser
o = Output(globals(),work_number=1)

X_1 = random.random() * 100 + random.random() * 100j
X_2 = random.random() *-100 + random.random() * 100j
X_3 = random.random() * 100 + random.random() *-100j
X_4 = random.random() * 100 + random.random() * 100j
X = (X_1*X_2)/(X_1-X_2) + (X_3*X_4)/(X_3+X_4) #@#
o.output()
```
