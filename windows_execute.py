import sys
from io import StringIO

from importlib import reload

import tkinter as tk
from tkinter import filedialog
import tkinter.ttk as ttk

# === Capture all output to StringIO === #
old_stdout = sys.stdout
old_stderr = sys.stderr

def term_print(*args):
    old_stdout.write(' '.join(args) + '\n')

out_log = StringIO()

# === Tk === #
def ask_file(root, box):
    global lispy
    out_log.truncate(0)
    out_log.seek(0)

    root.filename = tk.filedialog.askopenfilename(initialdir = ".", title = "Select LISPY file",filetypes = (("LISPY File","*.lispy"),("all files","*")))
    
    term_print('File found:', root.filename)

    import lispy
    from lispy import config

    config.EXIT_ON_ERROR = False
    config.COLORS = False
    

    sys.stdout = out_log
    sys.stderr = out_log
    
    lispy.run(root.filename)
    
    sys.stdout = old_stdout
    sys.stderr = old_stderr
    
    print('refs to lispy: ', sys.getrefcount(lispy))
    if 'lispy' in  sys.modules:
        del sys.modules['lispy.config']
        del lispy.config
        del sys.modules['lispy.visitor']
        del lispy.visitor
        del sys.modules['lispy.parsing']
        del lispy.parsing
        del sys.modules['lispy.lexing']
        del lispy.lexing
        del sys.modules['lispy.tree']
        del lispy.tree
        del sys.modules['lispy.err']
        del lispy.err
        del sys.modules['lispy']
        del lispy
        del config
    try:
        print('refs now: ', sys.getrefcount(lispy))
    except:
        print('lispy not found')
        print('modules: ', sys.modules.keys())
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

