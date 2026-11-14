import sys, pathlib
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)
code = pathlib.Path("slip_gen_boundary.py").read_text(encoding="utf-8")
exec(compile(code, "slip_gen_boundary.py", "exec"))
