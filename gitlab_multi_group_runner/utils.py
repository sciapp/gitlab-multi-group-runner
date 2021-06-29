from typing import Any, Dict, Mapping, TextIO

import yaml

try:
    from pygments import highlight
    from pygments.formatters import TerminalFormatter
    from pygments.lexers import get_lexer_by_name

    _pygments_available = True
except ImportError:
    _pygments_available = False


def dump_config_as_yaml(config_dict: Dict[str, Any], config_file: TextIO) -> None:
    text = yaml.dump(config_dict, default_flow_style=False)
    if config_file.isatty() and _pygments_available:
        lexer = get_lexer_by_name("yaml", stripall=True)
        formatter = TerminalFormatter()
        text = highlight(text, lexer, formatter)
    config_file.write(text)
    config_file.flush()


def recursive_update(d: Dict[Any, Any], u: Mapping[Any, Any]) -> Dict[Any, Any]:
    for k, v in u.items():
        if isinstance(v, Mapping):
            d[k] = recursive_update(d.get(k, {}), v)
        else:
            d[k] = v
    return d
