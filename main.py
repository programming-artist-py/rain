import zipfile
import os

class InvalidArguments(Exception): pass
class ParentNotFound(Exception): pass
class ConditionNotFound(Exception): pass
class InvalidCommand(Exception): pass
class ConditionNotCondition(Exception): pass
class IncludesNotSpecifiedUponNeed(Exception): pass
class InvalidSequenceOfOperatives(Exception): pass
included_files = set()

def get_rainc_dir():
    if os.name == "nt":
        return os.path.join(os.getenv("LOCALAPPDATA"), "rainc")
    else:
        return os.path.expanduser("~/.rainc")

def load_includes():
    incl_file = os.path.join(get_rainc_dir(), "incl", "INCLUDE")
    packages_dir = os.path.join(get_rainc_dir(), "packages")
    includes = {}
    if not os.path.exists(incl_file):
        return includes
    with open(incl_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or "@" not in line:
                continue
            pkg, path = line.split("@", 1)
            pkg = pkg.strip()
            path = path.strip().strip('"')
            full_path = os.path.normpath(os.path.join(get_rainc_dir(), path))
            includes[pkg] = full_path
    return includes

def load_from_include_file(incl_path):
    """Load include definitions from a provided INCL file, always relative to the rainc dir."""
    includes = {}
    rainc_dir = get_rainc_dir()

    if not os.path.exists(incl_path):
        raise FileNotFoundError(f"Include file `{incl_path}` not found.")

    with open(incl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or "@" not in line:
                continue

            pkg, path = line.split("@", 1)
            pkg = pkg.strip()
            path = path.strip().strip('"')

            # Always relative to rainc_dir
            full_path = os.path.normpath(os.path.join(rainc_dir, path))
            includes[pkg] = full_path

    return includes

def objectify(code, base_dir=".", included=None, debug=False):
    if included is None:
        included = set()
    objects = {}
    parents = {}
    conditions = {}
    calls = []
    code = [line.strip() for line in code if line.strip()]
    i = 0
    while i < len(code):
        line = code[i]
        if line.startswith("#"):
            i += 1
            continue
        elif line.startswith(":") and "{" in line:
            # Object definition
            line_clean = line.replace(" ", "")
            header, _ = line_clean.split("{", 1)

            name = header.split(":", 1)[1]
            parent = None
            condition = None
            first = None
            

            char = None
            idx = 0
            while idx < len(header) - 1:
                curr = header[idx]
                nxt = header[idx + 1]

                if curr == "?" and nxt == "?":
                    first = "??"
                    break
                elif curr == ">" and nxt == ">":
                    first = ">>"
                    break

                idx += 1


            if first == ">>":
                name, after = header.split(">>", 1)
                name = name.replace(":", "").strip()
                if "??" in after:
                    parent, condition = after.split("??", 1)
                    conditions[name] = condition
                elif ">>" in after:
                    raise InvalidSequenceOfOperatives(f"object {name} has an invalid sequence,\nit uses >> twice when only a singular >> is permitted")
                else:
                    parent = after
                parents[name] = parent
            elif first == "??":
                name, after = header.split("??", 1)
                name = name.replace(":", "").strip()
                if ">>" in after:
                    objA = name
                    objBandC = str(after).split(">>", 1)
                    objB = objBandC[0]
                    objC = objBandC[1]
                    raise InvalidSequenceOfOperatives(f"object {name} has an invalid sequence,\nit uses {objA} ?? {objB} >> {objC},\nto have a valid sequence, use {objA} >> {objB} ?? {objC}")
                elif "??" in after:
                    raise InvalidSequenceOfOperatives(f"object {name} has an invalid sequence,\nit uses ?? twice when only a singular ?? is permitted")
                else:
                    condition = after
                    conditions[name] = condition
            content = []
            i += 1
            while i < len(code):
                line = code[i].strip()
                if line.startswith("#"):
                    i += 1
                    continue
                if "}" in line:
                    break
                content.append(line)
                i += 1
            objects[name] = content
        elif line.startswith("~"):
            ref = line[1:].strip()
            if ref.startswith("incl/"):
                pkg = ref.split("/", 1)[1]
                if debug:
                    print("[runtime] Including package:", pkg)
                try:
                    if not INCLUDES:
                        pass
                except NameError:
                    raise IncludesNotSpecifiedUponNeed(
                        "This Rain project references RPM packages (~incl/...) but no include file was specified.\n"
                        "To use RPM packages, create an include file (e.g. INCL) and rerun with `-i INCL`.\n"
                        "If you don't know how to structure one, rerun with `-i rainc/incl/INCLUDE` to use your global include list (slower if many packages are installed)."
                    )
                if pkg not in INCLUDES:
                    raise InvalidArguments(f"Package `{pkg}` not found in INCLUDE file.")

                zip_path = INCLUDES[pkg]
                if not os.path.isfile(zip_path):
                    raise InvalidArguments(f"Package zip `{zip_path}` does not exist.")

                with zipfile.ZipFile(zip_path, "r") as z:
                    for name in z.namelist():
                        if not name.endswith(".rain"):
                            continue
                        with z.open(name) as f:
                            ref_code = [line.decode("utf-8").strip("\n") for line in f.readlines()]
                        ref_objects, ref_calls, ref_parents, ref_conditions = objectify(ref_code, base_dir=".", included=included)
                        conditions.update(ref_conditions)
                        objects.update(ref_objects)
                        calls.extend(ref_calls)
                        parents.update(ref_parents)
            elif ref.startswith("@BUILT_PACK/"):
                pkg = ref.split("/", 1)[1]
                if debug:
                    print("[runtime] Including built package:", pkg)
                if pkg not in INCLUDES:
                    raise InvalidArguments(f"Built package `{pkg}` not found in INCLUDES.")

                folder_path = INCLUDES[pkg]
                if not os.path.isdir(folder_path):
                    raise InvalidArguments(f"Built package folder `{folder_path}` does not exist.")

                for root, _, files in os.walk(folder_path):
                    for file in files:
                        if not file.endswith(".rain"):
                            continue
                        filename = os.path.join(root, file)
                        if filename in included:
                            continue
                        included.add(filename)
                        with open(filename, "r", encoding="utf-8") as f:
                            ref_code = f.readlines()
                        ref_objects, ref_calls, ref_parents = objectify(ref_code, os.path.dirname(filename), included, debug=debug)
                        objects.update(ref_objects)
                        calls.extend(ref_calls)
                        parents.update(ref_parents)
            else:
                filename = os.path.normpath(os.path.join(base_dir, line[1:].strip()))
                if filename in included:
                    i += 1
                    continue
                included.add(filename)

                if not os.path.isfile(filename):
                    raise InvalidArguments(f"Referenced file `{filename}` does not exist.")
                with open(filename, "r") as f:
                    ref_code = f.readlines()

                ref_objects, ref_calls, ref_parents = objectify(ref_code, os.path.dirname(filename), included)
                objects.update(ref_objects)
                calls.extend(ref_calls)
                parents.update(ref_parents)
        elif ":" in line:
            call_name, args_str = line.split(":", 1)
            call_name = call_name.strip()
            args_str = args_str.strip()
            args = []
            if args_str.startswith("(") and args_str.endswith(")"):
                args_inside = args_str[1:-1]
                args = [arg.strip() for arg in args_inside.split(";") if arg.strip()]
            calls.append((call_name, args))
        i += 1
    return objects, calls, parents, conditions

def run_objectified(objects, calls, parents, conditions, debug=False):
    variables = {"default": {"type": "int", "value": 0, "mut": False}}

    for child, parent in parents.items():
        if parent not in objects:
            spacing = (len(child)) + (len(parent) / 1.2) + 1
            raise ParentNotFound(f"parent.unknown({parent})\n:{child} >> {parent}\n{' ' * (int(spacing))}^^^\n`{parent}` is not a defined object")

    for object, condition in conditions.items():
        if condition not in objects:
            spacing = (len(object)) + (len(condition) / 1.2) + 1
            raise ConditionNotFound(f"condition.unknown({condition})\n:{object} ?? {condition}\n{' ' * (int(spacing))}^^^\n`{condition}` is not a defined object")

    def run_object(name, vars_copy, ignore_op=False):
        norun = False

        # Handle inheritance
        if name in parents and not ignore_op:
            parent = parents[name]
            if debug:
                print(f"[inherit] {name} inherits from {parent}")
            run_object(parent, vars_copy)

        # Handle conditional objects
        if name in conditions and not ignore_op:
            condition = conditions[name]
            if debug:
                print(f"[condition] {name} checks {condition}")

            ret = run_object(condition, vars_copy)

            if not isinstance(ret, bool):
                spacing = (len(name)) + int(len(condition) / 1.2) + 1
                raise ConditionNotCondition(
                    f"condition.notcondition({condition})\n"
                    f":{name} ?? {condition}\n"
                    f"{' ' * spacing}^^^\n"
                    f"`{condition}` does not return a boolean value.\n"
                    f"This makes `{condition}` invalid as a condition."
                )

            if not ret:
                norun = True

        # Execute object body
        if not norun:
            for command_line in objects[name]:
                parts = command_line.split()
                if not parts:
                    continue

                cmd, *args = parts
                run_command(vars_copy, cmd, args, name)

                if debug:
                    print(vars_copy)

        # Return __ret__ if set
        if "__res__" in vars_copy:
            ret_val = vars_copy["__res__"]
            if isinstance(ret_val, bool):
                return ret_val

        return None

    for call_name, call_args in calls:
        if call_name not in objects:
            raise InvalidArguments(f"Object `{call_name}` is not defined.")
        if debug:
            print(f"[call] Running `{call_name}`")

        arg_vars = {f"({i+1})": arg for i, arg in enumerate(call_args)}
        vars_copy = variables.copy()
        vars_copy.update(arg_vars)

        run_object(call_name, vars_copy)
        variables.update(vars_copy)

def run_command(variables, command, args, object_name):
    if command == "SET":
        if len(args) != 2:
            args_string = " ".join(args)
            spacing = 3 + len(args_string) / 2
            raise InvalidArguments(f"function.invalidarguments({args_string})\nSET {args_string}\n{' '*int(spacing)}^^^\ncommand SET only accepts 2 arguments, VAR and VAL.")
        key, val = args
        if val in variables:
            val = variables[val]
        try:
            val = int(val)
        except (ValueError, TypeError):
            pass
        variables[key] = val
    elif command == "ADD":
        if len(args) != 3:
            args_string = " ".join(args)
            spacing = 3 + len(args_string) / 2
            raise InvalidArguments(f"function.invalidarguments({args_string})\nADD {args_string}\n{' '*int(spacing)}^^^\ncommand ADD only accepts 3 arguments, VAROUT, VARINa and VARINb.")
        target, a, b = args
        val_a = int(variables.get(a, a))
        val_b = int(variables.get(b, b))
        variables[target] = val_a + val_b
    elif command == "PRINT":
        stopped = False
        output = []
        for arg in args:
            argument = arg
            if arg in variables:
                argument = str(variables[argument])
            argument = str(argument)
            if argument.startswith("(") and argument.endswith(")"):
                if argument not in variables:
                    print(f"mutable.unknown({argument.replace('(', '').replace(')', '')})")
                    stopped = True
            if argument.startswith('"') and arg.endswith('"'):
                argument = arg.strip('"')
            elif argument.startswith("'") and arg.endswith("'"):
                argument = argument.strip("'")
            output.append(argument)
        if not stopped:
            print(" ".join(output))
    elif command == "RET":
        expr = " ".join(args).strip()

        if not expr:
            raise InvalidArguments("RET requires an expression or value.")

        # Handle simple literals
        if expr.lower() in ["true", "false"]:
            variables["__ret__"] = expr.lower() == "true"
            return

        # Tokenize (split while keeping operators)
        tokens = []
        current = ""
        for ch in expr:
            if ch in "=!<>":
                if current.strip():
                    tokens.append(current.strip())
                    current = ""
                current += ch
            elif ch == " ":
                if current.strip():
                    tokens.append(current.strip())
                    current = ""
            else:
                # When previous token was an operator like "<=" etc.
                if current in ["=", "!", "<", ">"]:
                    if len(current) == 1 or current in ["<", ">", "!"]:
                        tokens.append(current)
                        current = ""
                current += ch
        if current.strip():
            tokens.append(current.strip())

        # Merge multi-char operators like "<=", ">=", "!="
        merged = []
        i = 0
        while i < len(tokens):
            if i + 1 < len(tokens) and (tokens[i] + tokens[i + 1]) in ["<=", ">=", "!="]:
                merged.append(tokens[i] + tokens[i + 1])
                i += 2
            else:
                merged.append(tokens[i])
                i += 1
        tokens = merged

        # Expect pattern like val op val op val op val ...
        if len(tokens) < 3:
            raise InvalidArguments(f"RET expression `{expr}` invalid (too short)")

        def try_cast(v):
            if v in variables:
                v = variables[v]
            try:
                if "." in str(v):
                    return float(v)
                else:
                    return int(v)
            except (ValueError, TypeError):
                return str(v).strip('"').strip("'")

        # Evaluate chained comparisons
        result = True
        i = 0
        while i < len(tokens) - 2:
            left = try_cast(tokens[i])
            op = tokens[i + 1]
            right = try_cast(tokens[i + 2])

            if op == "=":
                ok = left == right
            elif op == "!=":
                ok = left != right
            elif op == "<":
                ok = left < right
            elif op == ">":
                ok = left > right
            elif op == "<=":
                ok = left <= right
            elif op == ">=":
                ok = left >= right
            else:
                raise InvalidArguments(f"RET expression invalid operator `{op}`")

            if not ok:
                result = False
                break

            i += 2  # move to next comparison in chain

        variables["__res__"] = result
    elif command == "EXST":
        if len(args) != 1:
            args_string = " ".join(args)
            spacing = 3 + len(args_string) / 2
            raise InvalidArguments(f"function.invalidarguments({args_string})\nEXST {args_string}\n{' '*int(spacing)}^^^\ncommand EXST only accepts 1 argument, VAR")
        if args[0] in variables: variables["__res__"] = True
        if args[0] not in variables: variables["__res__"] = False
    else:
        spacing = max(0, int(len(command) / 2) - 1)
        raise InvalidCommand(f"command.unknown({command})\n{command}\n{' '*int(spacing)}^^^\ninvalid command `{command}` in object `{object_name}`")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run a Rain file")
    parser.add_argument("file", type=str, help="the Rain file to run")
    parser.add_argument("-i", "--include", type=str, help="Optional INCLUDE file for package references")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug mode.")
    args = parser.parse_args()

    with open(args.file) as f:
        code = f.readlines()

    if args.include == "rainc/incl/INCLUDE":
        INCLUDES = load_includes()
    elif args.include:
        INCLUDES = load_from_include_file(args.include)

    objs, calls, parents, conditions = objectify(code, base_dir=os.path.dirname(os.path.abspath(args.file)), debug=args.debug)
    run_objectified(objs, calls, parents, conditions, debug=args.debug)