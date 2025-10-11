import zipfile
import os

class InvalidArguments(Exception):
    pass

class ParentNotFound(Exception):
    pass

class InvalidCommand(Exception):
    pass

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

def objectify(code, base_dir=".", included=None, debug=False):
    if included is None:
        included = set()
    objects = {}
    parents = {}
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
            name = line.split(":", 1)[1].split("{", 1)[0].strip()
            if ">>" in name:
                name = line.split(">>", 1)[0].replace(" ", "").replace(":", "")
                parent = line.split(">>", 1)[1].replace(" ", "").replace("{", "")
                parents[name] = parent
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
                if pkg not in INCLUDES:
                    raise InvalidArguments(f"Package `{pkg}` not found in INCLUDE file.")

                zip_path = INCLUDES[pkg]
                if not os.path.isfile(zip_path):
                    raise InvalidArguments(f"Package zip `{zip_path}` does not exist.")

                with zipfile.ZipFile(zip_path, "r") as z:
                    # Load all .rain files in the zip
                    for name in z.namelist():
                        if not name.endswith(".rain"):
                            continue
                        with z.open(name) as f:
                            ref_code = [line.decode("utf-8").strip("\n") for line in f.readlines()]
                        ref_objects, ref_calls = objectify(ref_code, base_dir=".", included=included)
                        objects.update(ref_objects)
                        calls.extend(ref_calls)
            elif ref.startswith("@BUILT_PACK/"):
                pkg = ref.split("/", 1)[1]
                if debug:
                    print("[runtime] Including built package:", pkg)
                if pkg not in INCLUDES:
                    raise InvalidArguments(f"Built package `{pkg}` not found in INCLUDES.")

                folder_path = INCLUDES[pkg]
                if not os.path.isdir(folder_path):
                    raise InvalidArguments(f"Built package folder `{folder_path}` does not exist.")

                # Walk through the folder and include all .rain files
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
                        ref_objects, ref_calls = objectify(ref_code, os.path.dirname(filename), included, debug=debug)
                        objects.update(ref_objects)
                        calls.extend(ref_calls)
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
    return objects, calls, parents

def run_objectified(objects, calls, parents, debug=False):
    variables = {"default": {"type": "int", "value": 0, "mut": False}}

    # Check that all parents exist
    for child, parent in parents.items():
        if parent not in objects:
            spacing = (len(child)) + (len(parent) / 1.2) + 1
            raise ParentNotFound(f"parent.unknown({parent})\n:{child} >> {parent}\n{" " * (int(spacing))}^^^\n`{parent}` is not a defined object")

    def run_object(name, vars_copy):
        """Run an object and its parent chain in order."""
        # If this object has a parent, run it first
        if name in parents:
            parent = parents[name]
            if debug:
                print(f"[inherit] {name} inherits from {parent}")
            run_object(parent, vars_copy)

        # Now run the current object
        for command_line in objects[name]:
            parts = command_line.split()
            if not parts:
                continue
            cmd, *args = parts
            run_command(vars_copy, cmd, args, name)
            if debug:
                print(vars_copy)

    # Handle calls
    for call_name, call_args in calls:
        if call_name not in objects:
            raise InvalidArguments(f"Object `{call_name}` is not defined.")
        if debug:
            print(f"[call] Running `{call_name}`")

        # Map mutable args to (1), (2), ...
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
            raise InvalidArguments(f"function.invalidarguments({args_string})\nSET {args_string}\n{" "*int(spacing)}^^^\ncommand SET only accepts 2 arguments, VAR and VAL.")
        key, val = args
        if val in variables:
            val = variables[val]
        # Try to convert to int if possible
        try:
            val = int(val)
        except (ValueError, TypeError):
            pass
        variables[key] = val
    elif command == "ADD":
        if len(args) != 3:
            raise InvalidArguments(f"function.invalidarguments({args_string})\nSET {args_string}\n{" "*int(spacing)}^^^\ncommand ADD only accepts 3 arguments, VAROUT, VARINa and VARINb")
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
                    print(f"mutable.unknown({argument.replace("(", "").replace(")", "")})")
                    stopped = True
            if argument.startswith('"') and arg.endswith('"'):
                argument = arg.strip('"')
            elif argument.startswith("'") and arg.endswith("'"):
                argument = argument.strip("'")
            output.append(argument)
        if not stopped:
            print(" ".join(output))
    else:
        command = command.replace(" ", "")
        if len(command) <= 3:
            spacing = 0
            if spacing < 0:
                spacing = 0
        else:
            spacing = int(len(command) / 2) - 1
            if spacing < 0:
                spacing = 0
        raise InvalidCommand(f"command.unknown({command})\n{command}\n{" "*int(spacing)}^^^\ninvalid command `{command}` in object `{object_name}`")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="run a Rain file")
    parser.add_argument("file", type=str, help="the Rain file to run")
    parser.add_argument("--debug", "-d", action="store_true", help="Enable debug mode.")
    args = parser.parse_args()

    with open(args.file) as f:
        code = f.readlines()

    INCLUDES = load_includes()
    objs, calls, parents = objectify(code, base_dir=os.path.dirname(os.path.abspath(args.file)), debug=args.debug)
    run_objectified(objs, calls, parents, debug=args.debug)