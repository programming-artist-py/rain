import os

class InvalidArguments(Exception):
    pass

included_files = set()

def objectify(code, base_dir=".", included=None):
    if included is None:
        included = set()
    objects = {}
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
            filename = os.path.normpath(os.path.join(base_dir, line[1:].strip()))
            if filename in included:
                i += 1
                continue
            included.add(filename)

            if not os.path.isfile(filename):
                raise InvalidArguments(f"Referenced file `{filename}` does not exist.")
            with open(filename, "r") as f:
                ref_code = f.readlines()

            ref_objects, ref_calls = objectify(ref_code, os.path.dirname(filename), included)
            objects.update(ref_objects)
            calls.extend(ref_calls)
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
    return objects, calls

def run_objectified(objects, calls, debug=False):
    variables = {"default": {"type": "int", "value": 0, "mut": False}}
    for call_name, call_args in calls:
        if call_name not in objects:
            raise InvalidArguments(f"Object `{call_name}` is not defined.")
        # Map arguments to (1), (2), ...
        arg_vars = {f"({i+1})": arg for i, arg in enumerate(call_args)}
        vars_copy = variables.copy()
        vars_copy.update(arg_vars)
        # Run object commands
        for command_line in objects[call_name]:
            parts = command_line.split()
            if not parts:
                continue
            cmd, *args = parts
            run_command(vars_copy, cmd, args)
            if debug:
                print(vars_copy)
        variables.update(vars_copy)

def run_command(variables, command, args):
    if command == "SET":
        if len(args) != 2:
            raise InvalidArguments("SET requires 2 arguments.")
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
            raise InvalidArguments("ADD requires 3 arguments.")
        target, a, b = args
        val_a = int(variables.get(a, a))
        val_b = int(variables.get(b, b))
        variables[target] = val_a + val_b
    elif command == "PRINT":
        output = []
        for arg in args:
            argument = arg
            if arg in variables:
                argument = str(variables[argument])
            argument = str(argument)
            
            if argument.startswith('"') and arg.endswith('"'):
                argument = arg.strip('"')
            elif argument.startswith("'") and arg.endswith("'"):
                argument = argument.strip("'")
            output.append(argument)
        print(" ".join(output))
    else:
        raise InvalidArguments(f"Unknown command `{command}`.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="run a Rain file")
    parser.add_argument("file", type=str, help="the Rain file to run")
    parser.add_argument("--debug", "-d", action="store_true", help="Enable debug mode.")
    args = parser.parse_args()

    with open(args.file) as f:
        code = f.readlines()

    objs, calls = objectify(code, base_dir=os.path.dirname(os.path.abspath(args.file)))
    run_objectified(objs, calls, debug=args.debug)