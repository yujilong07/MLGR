"""Python -> LaTeX with google/latexify_py.

latexify.get_latex() takes a live function object, i.e. the user's code would have to be
executed on the server first (decorators and default values run arbitrary code). Here the
same latexify pipeline is fed an AST from ast.parse() instead — the code is never run."""
import ast
import textwrap

from latexify import codegen, transformers
from latexify import config as latexify_config

MAX_SOURCE_CHARS = 5000


class PythonFormulaError(ValueError):
    pass


def _function_tree(source: str) -> tuple[ast.Module, bool]:
    """Module with exactly one FunctionDef, and whether to show the signature f(x) = ..."""
    try:
        tree = ast.parse(textwrap.dedent(source).strip())
    except SyntaxError as exc:
        raise PythonFormulaError(f"Синтаксична помилка в рядку {exc.lineno}: {exc.msg}") from exc

    funcs = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    if funcs:
        func, signature = funcs[0], True
    elif len(tree.body) == 1 and isinstance(tree.body[0], ast.Expr):
        # A bare expression: "a * x**2 + b"
        func = ast.FunctionDef(
            name="f", args=ast.arguments(posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[]),
            body=[ast.Return(value=tree.body[0].value)], decorator_list=[], returns=None, type_params=[],
        )
        signature = False
    elif len(tree.body) == 1 and isinstance(tree.body[0], ast.Assign) and len(tree.body[0].targets) == 1 \
            and isinstance(tree.body[0].targets[0], ast.Name):
        # "y = a * x + b" -> y(...) = a x + b, shown without the argument list
        target = tree.body[0].targets[0].id
        func = ast.FunctionDef(
            name=target, args=ast.arguments(posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[]),
            body=[ast.Return(value=tree.body[0].value)], decorator_list=[], returns=None, type_params=[],
        )
        signature = "assign"
    else:
        raise PythonFormulaError("Потрібна функція (def ...), вираз або присвоєння на кшталт y = a*x + b")

    func.decorator_list = []
    module = ast.Module(body=[func], type_ignores=[])
    return ast.fix_missing_locations(module), signature


def python_to_latex(source: str, reduce_assignments: bool = True) -> str:
    if not source or not source.strip():
        raise PythonFormulaError("Вставте функцію або вираз")
    if len(source) > MAX_SOURCE_CHARS:
        raise PythonFormulaError("Занадто довгий код")

    tree, signature = _function_tree(source)
    config = latexify_config.Config.defaults().merge(reduce_assignments=reduce_assignments)

    # Same transformations latexify.get_latex() applies
    tree = transformers.AugAssignReplacer().visit(tree)
    if config.prefixes is not None:
        tree = transformers.PrefixTrimmer(config.prefixes).visit(tree)
    if config.reduce_assignments:
        tree = transformers.DocstringRemover().visit(tree)
        tree = transformers.AssignmentReducer().visit(tree)

    try:
        latex = codegen.FunctionCodegen(
            use_math_symbols=True,
            use_signature=signature is True,
            use_set_symbols=config.use_set_symbols,
        ).visit(tree)
    except Exception as exc:  # LatexifyError subclasses and unsupported nodes
        raise PythonFormulaError(f"latexify не зміг перетворити цей код: {exc}") from exc

    latex = latex.replace(r"\mathopen{}", "").replace(r"\mathclose{}", "")
    if signature == "assign":
        latex = f"{tree.body[0].name} = {latex}"
    return latex
