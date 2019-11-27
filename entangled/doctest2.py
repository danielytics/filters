## ------ language="Python" file="entangled/doctest2.py"
from pandocfilters import (applyJSONFilters)
from collections import defaultdict
from typing import (List, Dict, Union, Optional)
from dataclasses import dataclass
from .tangle import (get_code, get_name)
import sys
import queue
from enum import Enum

@dataclass
class CodeBlock:
    """Mocks the `panflute.CodeBlock` class."""
    text: str
    identifier: str
    classes: List[str]
    attributes: Dict[str, str]

## ------ begin <<read-config>>[0]
import subprocess
import json

def read_config():
    result = subprocess.run(
        ["dhall-to-json", "--file", "entangled.dhall"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8', check=True)
    return json.loads(result.stdout)

def get_language_info(config, identifier):
    return next(lang for lang in config["languages"]
                if identifier in lang["identifiers"])
## ------ end
## ------ begin <<doctest-session>>[0]
class TestStatus(Enum):
    PENDING = 0
    SUCCESS = 1
    FAIL = 2
    ERROR = 3
    UNKNOWN = 4

@dataclass
class Test:
    __test__ = False    # not a pytest class
    code: str
    expect: Optional[str]
    result: Optional[str] = None
    error: Optional[str] = None
    status: TestStatus = TestStatus.PENDING

@dataclass
class Suite:
    code_blocks: List[Test]
    language: str

import jupyter_client

def run_suite(config, s: Suite):
    info = get_language_info(config, s.language)
    kernel_name = info["jupyter"]
    if not kernel_name:
        raise RuntimeError(f"No Jupyter kernel known for the {s.language} language.")
    specs = jupyter_client.kernelspec.find_kernel_specs()
    if kernel_name not in specs:
        raise RuntimeError(f"Jupyter kernel `{kernel_name}` not installed.")

    repl_log = []
    with jupyter_client.run_kernel(kernel_name=kernel_name) as kc:
        print(f"Kernel `{kernel_name}` running ...", file=sys.stderr)
        def jeval(test: Test):
            msg_id = kc.execute(test.code)
            while True:
                try:
                    msg = kc.get_iopub_msg(timeout=1000)
                    if msg["msg_type"] == "execute_result" and \
                            msg["parent_header"]["msg_id"] ==  msg_id:
                        data = msg["content"]["data"]
                        if "text/plain" in data:
                            test.result = data["text/plain"]
                            if (test.expect is None) or test.result.strip() == test.expect.strip():
                                test.status = TestStatus.SUCCESS
                            else:
                                test.status = TestStatus.FAIL
                            return
                        else:
                            test.status = TestStatus.UNKNOWN
                            test.result = str(data)
                            return
                    if msg["msg_type"] == "status" and \
                            msg["parent_header"]["msg_id"] == msg_id and \
                            msg["content"]["execution_state"] == "idle":
                        if test.expect is None:
                            test.status = TestStatus.SUCCESS
                        else:
                            test.status = TestStatus.FAIL
                        return
                    if msg["msg_type"] == "error":
                        test.error = "\n".join(msg["content"]["traceback"])
                        test.status = TestStatus.ERROR 
                        return
                except queue.Empty:
                    test.error = "Operation timed out."
                    test.status = TestStatus.ERROR
                    return

        for test in s.code_blocks:
            jeval(test)
            if test.status is TestStatus.ERROR:
                break

    return s
## ------ end
## ------ begin <<get-doc-tests>>[0]
def get_language(c: CodeBlock) -> str:
    if not c.classes:
        name = get_name(c)
        raise ValueError(f"Code block `{name}` has no language specified.")
    return c.classes[0]

def get_doc_tests(code_map: Dict[str, List[CodeBlock]]) -> Dict[str, Suite]:
    def convert_code_block(c: CodeBlock) -> Test:
        if "doctest" in c.classes:
            s = c.text.split("\n---\n")
            name = get_name(c)
            if len(s) != 2:
                raise ValueError(f"Doc test `{name}` should have single `---` line.")
            return Test(*s)
        else:
            return Test(c.text, None)

    result = {}
    for k, v in code_map.items():
        if any("doctest" in c.classes for c in v):
            result[k] = Suite(
                code_blocks=[convert_code_block(c) for c in v],
                language=get_language(v[0]))

    return result
## ------ end
## ------ begin <<doctest2-action>>[0]
def tangle_action(code_map):
    def action(key, value, fmt, meta):
        if key == "CodeBlock":
            identifier, classes, attributes = value[0]
            c = CodeBlock(value[1], identifier, classes, dict(attributes))
            name = get_name(c)
            code_map[name].append(c)
        return []
    return action

def main():
    config = read_config()
    code_map = defaultdict(list)
    json_data = sys.stdin.read()
    output_json = applyJSONFilters([tangle_action(code_map)], json_data)
    suites = get_doc_tests(code_map)
    for name, s in suites.items():
        run_suite(config, s)
        print(s, file=sys.stderr)
    sys.stdout.write(output_json)
## ------ end
## ------ end
