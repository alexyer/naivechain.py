import json
import re
from typing import Callable

camel_re = re.compile(r'([A-Z])')
under_re = re.compile(r'(_[a-z])')


def camel_to_underscore(string: str) -> str:
    return camel_re.sub(lambda x: '_' + x.group(1).lower(), string)


def underscore_to_camel(string: str) -> str:
    return under_re.sub(lambda x: x.group(1).upper()[1], string)


def convert_json(json_obj: dict, convert_func: Callable[[str], str]) -> dict:
    new_dict = {}

    for i in json_obj.keys():
        if isinstance(i, dict):
            new_dict[i] = convert_json(json_obj[i], convert_func)
        elif isinstance(i, list):
            new_list = []
            for j in json_obj[i]:
                new_list.append(convert_json(j, convert_func))
            new_dict[convert_func(i)] = new_list
        else:
            new_dict[convert_func(i)] = json_obj[i]
    return new_dict


def convert_loads(*args, **kwargs):
    json_obj = json.loads(*args, **kwargs)
    return convert_json(json_obj, camel_to_underscore)


def convert_dumps(*args, **kwargs):
    args = (convert_json(args[0], underscore_to_camel),) + args[:1]
    return json.dumps(*args, **kwargs)
