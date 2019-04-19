import sys
from io import StringIO
from importlib.machinery import SourceFileLoader

import lispy
lispy.config.EXIT_ON_ERROR = False
execute = SourceFileLoader('execute', 'execute').load_module()
lispy.config.COLORS = False

import tkinter as tk
from tkinter import filedialog
import tkinter.ttk as ttk

ARGV = sys.argv

# === Capture all output to StringIO === #
old_stdout = sys.stdout
old_stderr = sys.stderr

def term_print(*args):
    old_stdout.write(' '.join(args) + '\n')

out_log = StringIO()
sys.stdout = out_log
sys.stderr = out_log

# === Tk === #
def ask_file(root, box):
    out_log.truncate(0)
    out_log.seek(0)

    root.filename = tk.filedialog.askopenfilename(initialdir = ".", title = "Select LISPY file",filetypes = (("LISPY File","*.lispy"),("all files","*")))
    
    ARGV.append(root.filename)
    execute.main()
    ARGV.pop()

    box.configure(state='normal')
    box.delete(1.0, tk.END)
    box.insert(1.0, out_log.getvalue())
    term_print('Inserted:\n', out_log.getvalue())
    box.configure(state='disabled')
    
def main():
    root = tk.Tk()
    root.title('LISPY - Graphical Interface')

    #root.attributes('-type', 'dialog')
    root.style = ttk.Style()
    root.style.theme_use('classic')
    root.configure(bg='white')
    
    frame = tk.Frame(root)
    frame.configure(bg='white')
    frame.pack(pady=10)

    label = tk.Label(frame, text="Pick a LISPY file to run:")
    label.configure(bg='white')
    label.pack(side='left', padx=(0, 20))
   
    _ = tk.Frame(root, bg='white')
    _.pack(fill=tk.X)
    label_box = tk.Label(_, text="Output:", justify=tk.LEFT)
    label_box.configure(bg='white', anchor='w')
    label_box.pack(side='left', padx=(10, 0))

    box = tk.Text(root, height=30, width=80)
    box.configure(state='disabled', bg='white')
    box.pack(padx=10, pady=(0,10))

    pick_button = tk.Button(
        frame,
        text='Choose File',
        command=lambda: ask_file(root, box)
    )
    pick_button.configure(bg='white')
    pick_button.pack(side='right', padx=(20, 0))

    tk.mainloop()



try:
    main()
except Exception as e:
    sys.stdout = old_stdout
    sys.stderr = old_stderr
    print(e)

sys.stdout = old_stdout
sys.stderr = old_stderr
# Restore STDOUT/STDERR.


print('Captured:')
print(out_log.getvalue())

