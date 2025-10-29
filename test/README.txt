this is a rain project created using the Rain Make Tool *RMT.
to compile this project, use the Rain Build Tool *RBT.
to run without compiling this project, use the Rain Run Tool *RRT.

RMT:

rainc make <project_name>

RBT:

rainc build [-c/--clean] -o/--output <output_file_name> <input_file_name> (for building only one file)
rainc build [-c/--clean] -m/--multiple -o/--output <output_file_name> "{<input_filename_a>, <input_filename_b>, <input_filename_c>}" (for building with multiple files)
rainc build --clear (clears build and dist folder)

RRT:

rainc run <file_name> (RRT can only run 1 file.)