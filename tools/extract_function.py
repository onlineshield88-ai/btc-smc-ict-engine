import ast
import sys
from pathlib import Path


def extract(source_file, function_name):

    source = Path(source_file).read_text(encoding="utf-8")

    tree = ast.parse(source)

    lines = source.splitlines()

    outdir = Path("tools/output")
    outdir.mkdir(parents=True, exist_ok=True)

    for node in tree.body:

        if isinstance(node, ast.FunctionDef):

            if node.name == function_name:

                start = node.lineno - 1
                end = node.end_lineno

                code = "\n".join(lines[start:end])

                outfile = outdir / f"{function_name}.py"

                outfile.write_text(code, encoding="utf-8")

                print(f"Saved -> {outfile}")

                return

    print("Function tidak ditemukan")


if __name__ == "__main__":

    if len(sys.argv) != 3:
        print("Usage:")
        print("python tools/extract_function.py engine.py add_indicators")
        sys.exit(1)

    extract(sys.argv[1], sys.argv[2])
