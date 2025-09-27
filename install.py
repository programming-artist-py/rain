import os
import shutil

# Determine installation directory
if os.name == "nt":
    install_dir = os.path.join(os.environ["LOCALAPPDATA"], "rainc")
else:
    install_dir = os.path.expanduser("~/.rainc")

os.makedirs(install_dir, exist_ok=True)

# Copy main.py
shutil.copy("main.py", install_dir)

# Copy tools folder
tools_src = os.path.join(os.getcwd(), "tools")
tools_dst = os.path.join(install_dir, "tools")
if os.path.exists(tools_dst):
    shutil.rmtree(tools_dst)
shutil.copytree(tools_src, tools_dst)

# Create CLI wrapper
rainc_py = os.path.join(install_dir, "rainc.py")
with open(rainc_py, "w", encoding="utf-8") as f:
    f.write(r'''#!/usr/bin/env python3
import sys
import os
import subprocess
import shutil

def uninstall():
    """Fully remove Rainc from the system."""
    if os.name == "nt":
        install_dir = os.path.join(os.environ["LOCALAPPDATA"], r"rainc")
        bat_path = os.path.join(os.environ["LOCALAPPDATA"], r"Microsoft\WindowsApps\rainc.bat")
        exe_path = os.path.join(os.environ["LOCALAPPDATA"], r"Microsoft\WindowsApps\rainc.exe")
    else:
        install_dir = os.path.expanduser("~/.rainc")
        symlink_path = "/usr/local/bin/rainc"

    # Remove installation folder
    if os.path.exists(install_dir):
        shutil.rmtree(install_dir)
        print(f"Removed installation folder: {install_dir}")

    # Remove CLI wrapper
    if os.name == "nt":
        if os.path.exists(bat_path):
            os.remove(bat_path)
            print(f"Removed CLI wrapper: {bat_path}")
        if os.path.exists(exe_path):
            os.remove(exe_path)
            print(f"Removed lingering WindowsApps entry: {exe_path}")
        # Remove App Execution Alias
        try:
            subprocess.run(
                ["powershell", "-Command",
                 r"Remove-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\App Paths\rainc.exe' -Name '(default)' -ErrorAction SilentlyContinue"],
                check=False
            )
            print("Removed any App Execution Alias for Rainc.")
        except Exception:
            pass
    else:
        if os.path.islink(symlink_path):
            os.remove(symlink_path)
            print(f"Removed CLI symlink: {symlink_path}")

    print("Rainc has been fully uninstalled.")
    sys.exit(0)

# ---- Main CLI logic ----
if len(sys.argv) < 2:
    print("Usage: rainc [-h|help|build|run|make|uninstall|-u] ...")
    sys.exit(1)

command = sys.argv[1]
args = sys.argv[2:]

home = os.path.dirname(os.path.abspath(__file__))
main_py = os.path.join(home, "main.py")
build_tool = os.path.join(home, "tools", "build")
make_tool = os.path.join(home, "tools", "make")

if command in ("-h", "help"):
    print("""Rain CLI Tool
            Usage: rainc [command] [arguments]
                Commands:
                    build <file.rain> -o <output_name> [--platform win|linux] : Compile a .rain file to an executable.
                    run <file.rain> : Run a .rain file directly.
                    uninstall | -u : Uninstall Rainc from the system.
                    make <project_name> : Create a new Rain project using the default template.
                    -h | help : Show this help message.
            
                Help Support:
                    build: yes ~rainc build -h
                    run: yes ~rainc run -h
                    uninstall: no
                    base: yes ~rainc -h/help""")
    sys.exit(0)
if command == "build":
    subprocess.run([sys.executable, build_tool] + args)
elif command == "run":
    subprocess.run([sys.executable, main_py] + args)
elif command == "make":
    subprocess.run([sys.executable, make_tool] + args)
elif command in ("uninstall", "-u"):
    uninstall()
    sys.exit(0)
else:
    print("Usage: rainc [build|run|uninstall|-u] ...")
''')


os.chmod(rainc_py, 0o755)

# Install CLI
if os.name == "nt":
    bat_path = os.path.join(os.environ["LOCALAPPDATA"], r"Microsoft\WindowsApps\rainc.bat")
    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(f"@echo off\npython \"{rainc_py}\" %*")
    print(f"Installed rainc CLI at {bat_path}")
else:
    symlink_path = "/usr/local/bin/rainc"
    if os.path.exists(symlink_path):
        os.remove(symlink_path)
    os.symlink(rainc_py, symlink_path)
    print(f"Installed rainc CLI at {symlink_path}")