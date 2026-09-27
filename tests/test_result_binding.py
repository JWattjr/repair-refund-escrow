import ast
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "contracts" / 'repair_refund_escrow.py'
OWNER_NAMES = ['_defect_review', '_repair_review']
CANDIDATE_NAMES = ['_defect_candidate', '_repair_candidate']
VECTOR_NAMES = ['_result_vector']
REQUIRED_COMPARE_KEYS = frozenset(['snapshot_digest', 'criterion_id', 'finding', 'citations'])
REQUIRED_SCHEMAS = tuple(frozenset(row) for row in [{'results', 'snapshot_digest'}, {'citations', 'criterion_id', 'finding'}])
BOUND_FUNCTION = '_defect_candidate'


def _functions(tree):
    return {n.name: n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def _literal_set(node):
    if isinstance(node, ast.Set) and all(isinstance(x, ast.Constant) and isinstance(x.value, str) for x in node.elts):
        return frozenset(x.value for x in node.elts)
    return None


def _schemas(node):
    found = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Compare):
            operands = [n.left, *n.comparators]
            if any(isinstance(x, ast.Call) and isinstance(x.func, ast.Name) and x.func.id == "set" for x in operands):
                found.update(value for x in operands if (value := _literal_set(x)) is not None)
        if isinstance(n, ast.Assign) and isinstance(n.value, ast.Set):
            names = {x.id for x in n.targets if isinstance(x, ast.Name)}
            if names & {"expected", "expected_fields"}:
                value = _literal_set(n.value)
                if value is not None:
                    found.add(value)
    return found


def _reads(node):
    return {n.slice.value for n in ast.walk(node) if isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Constant) and isinstance(n.slice.value, str)}


def _call_name(node):
    if not isinstance(node, ast.Call):
        return None
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def _has_calldata(node):
    return any(isinstance(n, ast.Attribute) and n.attr == "calldata" and isinstance(n.value, ast.Name) and n.value.id == "leader_result" for n in ast.walk(node))


def _has_snapshot_binding(node):
    for compare in (n for n in ast.walk(node) if isinstance(n, ast.Compare)):
        refs = {(n.value.id, n.slice.value) for n in ast.walk(compare)
                if isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name)
                and isinstance(n.slice, ast.Constant) and isinstance(n.slice.value, str)}
        if ("raw", "snapshot_digest") in refs and ("snapshot", "snapshot_digest") in refs:
            return True
    return False


def _paired_keys(compare):
    left = {n.slice.value for n in ast.walk(compare.left) if isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name) and n.value.id == "leader" and isinstance(n.slice, ast.Constant) and isinstance(n.slice.value, str)}
    right = {n.slice.value for operand in compare.comparators for n in ast.walk(operand) if isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name) and n.value.id == "mine" and isinstance(n.slice, ast.Constant) and isinstance(n.slice.value, str)}
    return left & right


def test_every_returned_judgment_field_is_compared_or_snapshot_bound():
    functions = _functions(ast.parse(SOURCE.read_text(encoding="utf-8")))
    actual_schemas = set()
    for name in CANDIDATE_NAMES:
        assert name in functions, f"missing candidate normalizer: {name}"
        actual_schemas.update(_schemas(functions[name]))
    for name in OWNER_NAMES:
        assert name in functions, f"missing assessment owner: {name}"
        actual_schemas.update(_schemas(functions[name]))
    missing_schemas = set(REQUIRED_SCHEMAS) - actual_schemas
    assert not missing_schemas, f"unvalidated leader result schema(s): {sorted(map(sorted, missing_schemas))}"

    compared = set()
    for name in VECTOR_NAMES:
        assert name in functions, f"missing comparison vector: {name}"
        compared.update(_reads(functions[name]))
    for owner_name in OWNER_NAMES:
        owner = functions[owner_name]
        nested = {n.name: n for n in ast.walk(owner) if isinstance(n, ast.FunctionDef)}
        assert "validator_fn" in nested, f"{owner_name} has no validator"
        validator = nested["validator_fn"]
        calls = [n for n in ast.walk(validator) if isinstance(n, ast.Call)]
        assert any(_call_name(n) in CANDIDATE_NAMES and _has_calldata(n) for n in calls), f"{owner_name} does not normalize leader_result.calldata"
        assert any(_call_name(n) == "run_nondet_unsafe" for n in ast.walk(owner) if isinstance(n, ast.Call)), f"{owner_name} does not run consensus validation"
        for compare in (n for n in ast.walk(validator) if isinstance(n, ast.Compare) and any(isinstance(op, ast.Eq) for op in n.ops)):
            compared.update(_paired_keys(compare))
            for name in VECTOR_NAMES:
                if _call_name(compare.left) == name and any(_call_name(x) == name for x in compare.comparators):
                    compared.update(_reads(functions[name]))
    missing = REQUIRED_COMPARE_KEYS - compared
    assert not missing, f"leader judgment fields are not compared to the validator result: {sorted(missing)}"
    if BOUND_FUNCTION:
        assert _has_snapshot_binding(functions[BOUND_FUNCTION]), "snapshot digest is not bound to frozen input"
