import re

value_token = re.compile(r'%[sS]%')
token = re.compile(r'%(.*?)%')
reval = re.compile(r'\((.*?)\)')
cleanup = re.compile(r',?%(WAIT\d+|TIME\d+|EVAL.*?)%,?')
hex_dec = re.compile(r'HEX([0-9A-F]*?)HEX')
mod = re.compile(r'MOD', re.IGNORECASE)
eval_filter = re.compile(r'[^0-9%*/+-.()]')
extra_comma = re.compile(r',+')
player = re.compile(r'^P(?:layer)*(\d)|$')
output_split = re.compile(' = |=')
