import re

token = re.compile(r'%(.*?)%')
var_token = re.compile(r'#(.*?)#', re.IGNORECASE)
skip = re.compile(r'\[(.*?)::([:\d]+)]', re.IGNORECASE)
eval_filter = re.compile(r'[^0-9%*/+-.()]')
hex_filter = re.compile(r'^[0-9a-fA-F]+$')
reval = re.compile(r'\((.*?)\)')
extra_comma = re.compile(r',+')
cleanup = re.compile(r',?%(WAIT\d+|TIME\d+|TIMR\d+)%,?')
player = re.compile(r'^P(?:layer)*(\d)|$')
output_split = re.compile(' = |=')
remap = re.compile(r'(\d+)TO(\d+)')
mod = re.compile(r'MOD', re.IGNORECASE)
