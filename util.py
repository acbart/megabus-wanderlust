'''

Various utility functions for the wanderlust library

'''

import json
import sys

_PYTHON_3 = sys.version_info >= (3, 0)

def to_ascii(s): 
    return "".join(filter(lambda x: ord(x)<128, s))
    
def csv_to_lod(filename, delimiter = ','):
    try:
        with open(filename) as csv_file:
            csv_file = csv.reader(csv_file, delimiter=delimiter)
            headers = next(csv_file, None) # Skip headers
            data = [dict(zip(headers, line)) for line in csv_file]
            return data
    except (OSError, IOError) as e:
        raise Exception('Error! Could not find the "{}" file. Make sure that it exists'.format(filename, __file__))
        
def _recursively_convert_unicode_to_str(input):
    """
    Force the given input to only use `str` instead of `bytes` or `unicode`.
    This works even if the input is a dict, list, 
    """
    if isinstance(input, dict):
        return {_recursively_convert_unicode_to_str(key): _recursively_convert_unicode_to_str(value) for key, value in input.items()}
    elif isinstance(input, list):
        return [_recursively_convert_unicode_to_str(element) for element in input]
    elif _PYTHON_3 and isinstance(input, str):
        return str(input.encode('ascii', 'replace').decode('ascii'))
    elif not _PYTHON_3 and isinstance(input, unicode):
        return str(input.encode('ascii', 'replace').decode('ascii'))
    else:
        return input
   
_DATA = None
def load_json(filename):
    global _DATA
    if not _DATA:
        _DATA = _recursively_convert_unicode_to_str(json.load(open(filename, 'r')))
    return _DATA

def safe_str(a_string):
    return a_string.replace(',', '_')
