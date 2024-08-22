import ast
from collections.abc import Collection
from pathlib import Path
from typing import IO, Any, Generator

basedir = Path(__file__).absolute().parent.parent


class Visitor(ast.NodeVisitor):
    def __init__(self, classes: list[str]):
        self.classes = classes
        self.messages: list[tuple[int, str, str]] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        if node.name in self.classes:
            for child in node.body:
                # Skip docstrings.
                if isinstance(child, ast.Expr) and isinstance(child.value, ast.Constant):
                    continue
                assert isinstance(child, ast.Assign) and isinstance(child.value, ast.Constant), ast.unparse(child)
                self.messages.append((child.value.lineno, child.value.value, node.name))


# https://babel.pocoo.org/en/latest/api/messages/extract.html#babel.messages.extract.extract_python uses tokenize,
# but it is easier with ast. (Compare to `python -m tokenize -e app/models.py`.)
def extract_enum(
    fileobj: IO[bytes], keywords: dict[str, Any], comment_tags: Collection[str], options: dict[str, Any]
) -> Generator[tuple[int, str, str, list[str]], None, None]:
    visitor = Visitor(options.get("classes", "").split(","))
    visitor.visit(ast.parse((basedir / "app" / "models.py").read_text()))
    for lineno, text, comment in visitor.messages:
        yield lineno, "", text, [comment]
