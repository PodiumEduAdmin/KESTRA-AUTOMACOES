from kestra import Kestra
import os

say = os.environ['SAY'] + "Hello"

Kestra.outputs(say)

