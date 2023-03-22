# Standard Library
import ast
import inspect
from typing import *

# Third-Party Library
from executing import Source
from colorama import Fore, Style, init

init(autoreset=True)

def red(msg: str) -> str:
    return f"{Fore.RED}{msg}"

def green(msg: str) -> str:
    return f"{Fore.GREEN}{msg}"

def yellow(msg: str) -> str:
    return f"{Fore.YELLOW}{msg}"

def type_check(obj: object, T: Union[type, Tuple[Type]]) -> None:
    global DEBUG
    call_frame = inspect.currentframe().f_back
    node: ast.Call = Source.executing(call_frame).node
    source: str = inspect.getsource(inspect.getmodule(call_frame))
    arg_name = ast.get_source_segment(source=source, node=node.args[0])
    type_name = ast.get_source_segment(source=source, node=node.args[1])
    assert isinstance(obj, T), red(f"{arg_name} should be type {type_name}, but received {type(obj)}")
    return True


if __name__ == "__main__":
    class A:
        def __init__(self) -> None:
            self.num = 1
    
    b = "123"
    type_check(b, (A, int))