# nback_experiment.py
import tkinter as tk
import time
import random
import csv
import sys
import os
import pyttsx3
from tkinter import ttk, messagebox
from pathlib import Path

# --- Config ---
STIMULUS_DURATION = 0.76  # seconds (760 ms) for main experiment
TUTORIAL_STIMULUS_DURATION = 2.0  # 3 seconds for tutorial
ITI_DURATION = 1.5  # seconds
TRAINING_TRIALS = 15
EXPERIMENT_TRIALS = 20
TARGET_PERCENTAGE = 0.2
N_LEVELS = [1, 2, 3, 4, 5]
DIGITS = list(range(10))
SEEDS = ['alpha', 'bravo', 'charlie', 'delta', 'echo']
CSV_PATH = 'sample_sheet.csv'
DEBUG = False  # Set to True for debugging output

# --- Turorial Instructions ---
NARRATIONS = {
    1: "Welcome to the N-back experiment. In this task, numbers will be presented on the screen one at a time. "
       "Pay attention to the numbers, and if the number on the screen is the same as the number N times before, "
       "press the spacebar. Press next to view examples.",
    2: "This is a 1-back example. Press the SPACEBAR when the number is the same as the previous number. "
       "In this sequence: 5, 3, 3 - you should press SPACE on the third number because it matches the previous number.",
    3: "This is a 2-back example. Press the SPACEBAR when the number is the same as the number shown two numbers ago. "
       "In this sequence: 5, 3, 5 - you should press SPACE on the third number because it matches the number two positions back.",
    4: "For the tutorial, you will practice both 1-back and 2-back tasks. During practice, you'll get immediate feedback "
       "on your responses. The tutorial includes 6 trials for each task with a mix of targets and non-targets. "
       "Remember: Press SPACE only if the number matches the one shown N positions back! "
       "When ready, press Start Training. If familiar with the task, you may Skip Training."
}

# Determine if running as executable
if getattr(sys, 'frozen', False):
    application_path = sys._MEIPASS
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

# --- Determine CSV Path ---
if getattr(sys, 'frozen', False):
    # Running as executable
    base_path = sys._MEIPASS  # For bundled resources
    exe_dir = os.path.dirname(sys.executable)  # For files alongside executable
    
    # Check both possible locations
    csv_paths = [
        os.path.join(exe_dir, 'sample_sheet.csv'),      # Alongside executable
        os.path.join(base_path, 'sample_sheet.csv')      # Inside bundle
    ]
    
    for path in csv_paths:
        if os.path.exists(path):
            CSV_PATH = path
            break
    else:
        # Fallback if not found
        CSV_PATH = os.path.join(exe_dir, 'sample_sheet.csv')
        if DEBUG:
            print(f"CSV not found, using: {CSV_PATH}")
else:
    # Running as script
    CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sample_sheet.csv')

if DEBUG:
    print(f"Using CSV path: {CSV_PATH}")

# --- State ---
participant_id = None
current_version = None
first_time_participant = False
experiment_data = []
trial_index = 0
block_index = 0
experiment_blocks = []
rng = None
current_instruction_page = 0

# --- Init voice engine ---
try:
    engine = pyttsx3.init()
    engine.setProperty('rate', 150) 
    engine.setProperty('rate', 150)
except Exception as e:
    engine = None
    print(f"TTS initialization failed: {e}")

def speak(text):
    """Speak text using TTS if available"""
    if not engine:
        return
    try:
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        if DEBUG:
            print(f"TTS Error: {str(e)}")

# --- Function Definitions ---
def seeded_rng(seed_word):
    """Create a seeded random number generator"""
    seed = sum(ord(c) for c in seed_word)
    return random.Random(seed)

def prepare_blocks(training=False):
    """Prepare blocks for the experiment"""
    global experiment_blocks, block_index, rng
    
    experiment_blocks = []
    seed_word = SEEDS[current_version - 1]
    rng = seeded_rng(seed_word)
    levels = N_LEVELS
    
    # Only include 1-back and 2-back for training
    if training:
        levels = [1, 2]  # Only 1-back and 2-back for training
    else:
        levels = N_LEVELS  # All levels for main experiment
    
    trial_count = TRAINING_TRIALS if training else EXPERIMENT_TRIALS
    
    for n in levels:
        trials = []
        target_indices = []
        
        # Only create targets if we have enough trials
        if trial_count > n:
            num_targets = max(1, int(trial_count * TARGET_PERCENTAGE))
            target_indices = rng.sample(range(n, trial_count), num_targets)
        
        for i in range(trial_count):
            is_target = False
            digit = None
            
            if i < n:
                # First n trials can't be targets
                digit = rng.choice(DIGITS)
            elif i in target_indices:
                # Target trial
                digit = trials[i - n]['digit']
                is_target = True
            else:
                # Non-target trial
                prev_digit = trials[i - n]['digit']
                # Efficient digit selection without creating a new list
                digit = rng.choice([d for d in DIGITS if d != prev_digit])
                
            trials.append({"digit": digit, "is_target": is_target})
        
        experiment_blocks.append({
            "n": n, 
            "trials": trials, 
            "training": training
        })
    
    block_index = 0
    if DEBUG:
        print(f"Prepared {len(experiment_blocks)} blocks")

def create_tutorial_block(n, sequences):
    """Create tutorial block with specified sequences"""
    trials = []
    for i, (digits, targets, feedbacks) in enumerate(sequences):
        trials.append({
            "digit": digits,
            "is_target": targets,
            "correct_response": targets,  # Should press for targets
            "feedback": feedbacks
        })
    return {
        "n": n,
        "trials": trials,
        "training": True
    }

def get_tutorial_blocks():
    """Generate tutorial blocks with optimized structure"""
    # Format: (digit, is_target, show_feedback)
    return [
        create_tutorial_block(1, [
            (5, False, False),  # First stimulus - no feedback
            (3, False, True),
            (3, True, True),
            (4, False, True),
            (4, True, True),
            (2, False, True)
        ]),
        create_tutorial_block(2, [
            (5, False, False),  # First stimulus - no feedback
            (3, False, True),
            (5, True, True),
            (6, False, True),
            (3, True, True),
            (7, False, True)
        ])
    ]

def start_block():
    """Start the current block"""
    global trial_index
    trial_index = 0
    stimulus_label.config(text="Starting 1-back...", fg="white")
    instruction_label.config(text="")
    feedback_label.config(text="")
    root.update_idletasks()  
    root.after(1500, run_trial)

def run_trial():
    """Run a single trial - no instructions or feedback for actual trials"""
    global trial_index, block_index
    
    stimulus_label.config(font=("Helvetica", 144, "bold"))
    
    if DEBUG:
        print(f"Block: {block_index}/{len(experiment_blocks)}, Trial: {trial_index}")
    
    # Check if all blocks are finished
    if block_index >= len(experiment_blocks):
        end_experiment()
        return
    
    block = experiment_blocks[block_index]
    trials = block['trials']
    
    # Check if current block is finished
    if trial_index >= len(trials):
        block_index += 1
        trial_index = 0
        
        if block_index < len(experiment_blocks):
            stimulus_label.config(text=f"{experiment_blocks[block_index]['n']}-back", fg="white")
            root.update_idletasks()  
            root.after(1500, run_trial)
        else:
            end_experiment()
        return
    
    # Show stimulus
    trial = trials[trial_index]
    stimulus_label.config(text=str(trial['digit']), fg='white')  # Always white for actual trials
    instruction_label.config(text="")  # No instructions for actual trials
    feedback_label.config(text="")  # No feedback for actual trials
    root.update_idletasks()  
    stimulus_onset = time.time() * 1000  # Record stimulus onset in ms (starting from epoch time, aka Jan 1, 1970)
    
    response = {'pressed': False, 'rt': None}
    rt_start = time.time() * 1000 # Record reaction time onset in ms (starting from epoch time, aka Jan 1, 1970)
    response_time_val = None
    
    def on_key_press(event):
        """Handle key press during stimulus presentation"""
        nonlocal response, response_time_val
        if event.keysym == 'space' and not response['pressed']:
            response['pressed'] = True
            response['rt'] = int((time.time() - rt_start) * 1000)
            response_time_val = time.time() * 1000  # Record response time in ms
            if DEBUG:
                print(f"Key pressed at {response['rt']}ms")

    # Bind key handler
    root.unbind('<Key>')
    root.bind('<Key>', on_key_press)
    
    def end_trial():
        """End the current trial - no feedback for actual trials"""
        nonlocal response, stimulus_onset, response_time_val
        global trial_index
        
        root.unbind('<Key>')
        
        # Calculate accuracy for logging
        accuracy = None
        if trial['is_target']:
            accuracy = response['pressed']
        else:
            accuracy = not response['pressed']

        # Log trial data
        trial_data = {
            "participant_id": participant_id,
            "version": current_version,
            "block_n": block['n'],
            "trial_index": trial_index,
            "stimulus_digit": trial['digit'],
            "is_target": trial['is_target'],
            "response": response['pressed'],
            "accuracy": accuracy,
            "rt": response['rt'],
            "stimulus_onset": stimulus_onset,
            "response_time": response_time_val,
            "training": block['training'],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        experiment_data.append(trial_data)

        # Show inter-trial interval indicator
        stimulus_label.config(font=("Helvetica", 48, "bold"), text="•", fg="white")
        root.update_idletasks()  
        
        trial_index += 1
        root.after(int(ITI_DURATION * 1000), run_trial)

    # Schedule end of trial
    root.after(int(STIMULUS_DURATION * 1000), end_trial)

def run_tutorial_trial():
    """Run a tutorial trial with immediate feedback and instructions"""
    global trial_index, block_index

    # Reset font to 144 at start of each trial
    stimulus_label.config(font=("Helvetica", 144, "bold"))
    
    tutorial_blocks = get_tutorial_blocks()
    
    # Check if all tutorial blocks are finished
    if block_index >= len(tutorial_blocks):
        show_frame(frame_transition)
        return
    
    block = tutorial_blocks[block_index]
    trials = block['trials']
    
    # Check if current block is finished
    if trial_index >= len(trials):
        block_index += 1
        trial_index = 0
        
        if block_index < len(tutorial_blocks):
            stimulus_label.config(text=f"{tutorial_blocks[block_index]['n']}-back", fg="white")
            instruction_label.config(text="")
            feedback_label.config(text="")
            root.update_idletasks()  
            root.after(1500, run_tutorial_trial)
        else:
            show_frame(frame_transition)
        return
    
    # Show stimulus
    trial = trials[trial_index]
    stimulus_label.config(text=str(trial['digit']), fg='white')
    instruction_label.config(text=f"Press SPACE if this number matches the one {block['n']} position{'s' if block['n'] > 1 else ''} back")
    feedback_label.config(text="")
    root.update_idletasks()  
    stimulus_onset = time.time() * 1000  # Record stimulus onset in ms (starting from epoch time, aka Jan 1, 1970)
    #note: time.time() measures in seconds since epoch time
    
    response = {'pressed': False, 'rt': None}
    rt_start = time.time() * 1000 # Record reaction time onset in ms (starting from epoch time, aka Jan 1, 1970)
    response_time_val = None
    feedback_shown = False
    
    def on_key_press(event):
        """Handle key press during stimulus presentation"""
        nonlocal response, response_time_val, feedback_shown
        if event.keysym == 'space' and not response['pressed']:
            response['pressed'] = True
            response['rt'] = int((time.time() - rt_start) * 1000)
            response_time_val = time.time() * 1000  # Record response time in ms
            
            # Only show feedback if allowed for this trial
            if trial['feedback']:
                # Determine if response was correct based on expected behavior
                correct = (response['pressed'] == trial['correct_response'])
                
                # Set color and feedback message
                if correct:
                    color = "green"
                    if response['pressed']:
                        feedback = "Correct! You pressed SPACE for a target."
                    else:
                        feedback = "Correct! You didn't press SPACE for a non-target."
                else:
                    color = "red"
                    if trial['is_target']:
                        feedback = "Missed a target! You should have pressed SPACE."
                    else:
                        feedback = "False alarm! You shouldn't press for non-targets."
                
                # Show immediate feedback
                stimulus_label.config(fg=color)
                feedback_label.config(text=feedback)
                feedback_shown = True
                root.update_idletasks()
            
            if DEBUG:
                print(f"Key pressed at {response['rt']}ms")

    # Bind key handler
    root.unbind('<Key>')
    root.bind('<Key>', on_key_press)
    
    def end_trial():
        """End the current trial with feedback if needed"""
        nonlocal response, stimulus_onset, response_time_val, feedback_shown
        global trial_index
        
        root.unbind('<Key>')

        # Show feedback at end of trial if not already shown and if allowed
        if not feedback_shown and trial['feedback']:
            # Determine if response was correct based on expected behavior
            correct = (response['pressed'] == trial['correct_response'])
            
            # Set color and feedback message
            if correct:
                color = "green"
                if response['pressed']:
                    feedback = "Correct! You pressed SPACE for a target."
                else:
                    feedback = "Correct! You didn't press SPACE for a non-target."
            else:
                color = "red"
                if trial['is_target']:
                    feedback = "Missed a target! You should have pressed SPACE."
                else:
                    feedback = "False alarm! You shouldn't press for non-targets."
            
            # Show feedback
            stimulus_label.config(fg=color)
            feedback_label.config(text=feedback)
            feedback_shown = True
            root.update_idletasks()
        
        # Log tutorial trial
        trial_data = {
            "participant_id": participant_id,
            "version": current_version,
            "block_n": block['n'],
            "trial_index": trial_index,
            "stimulus_digit": trial['digit'],
            "is_target": trial['is_target'],
            "response": response['pressed'],
            "accuracy": (response['pressed'] == trial['correct_response']) if trial['feedback'] else None,
            "rt": response['rt'],
            "stimulus_onset": stimulus_onset,
            "response_time": response_time_val,
            "training": True,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        experiment_data.append(trial_data)
        
        # Show feedback for 1.5 seconds, then show ITI dot
        root.after(1500, show_iti)
    
    def show_iti():
        """Show inter-trial interval after feedback duration"""
        global trial_index  # Add this line to access the global variable
        # Show inter-trial interval indicator
        stimulus_label.config(font=("Helvetica", 48, "bold"), text="•", fg="white")
        root.update_idletasks()  
        
        # Move to next trial after ITI delay 
        trial_index += 1
        root.after(int(ITI_DURATION * 1000), run_tutorial_trial)
    
    # Schedule end of trial
    root.after(int(TUTORIAL_STIMULUS_DURATION * 1000), end_trial)

def redo_tutorial():
    """Reset and restart the tutorial"""
    global trial_index, block_index
    trial_index = 0
    block_index = 0
    show_frame(frame_experiment)
    stimulus_label.config(text="Restarting tutorial...", fg="white")
    instruction_label.config(text="")
    feedback_label.config(text="")
    root.update_idletasks()
    root.after(1500, run_tutorial_trial)

def end_experiment():
    """End the experiment"""
    if experiment_blocks and experiment_blocks[0].get('training', False):
        show_frame(frame_transition)
    else:
        filepath = save_data()
        show_frame(frame_end)

def save_data():
    """Save experiment data to CSV"""
    
    if not experiment_data:
        messagebox.showerror("Error", "No data to save")
        return

    # Filter out training trials
    experimental_data = [
        trial for trial in experiment_data 
        if not trial.get('training', True) 
    ]
    
    if not experimental_data:
        messagebox.showerror("Error", "No experimental data to save")
        return

    # Determine output directory - use Documents folder
    documents_dir = Path.home() / "Documents"
    filename = f"nback_{participant_id}_v{current_version}.csv"
    filepath = documents_dir / filename
    
    try:
        with open(filepath, 'w', newline='') as f:
            fieldnames = [
            "Participant ID", "Version", "Block N", "Trial Index", 
            "Stimulus Digit", "Is Target", "Response", "Accuracy",
            "Reaction Time (ms)", "Stimulus Onset (ms)", "Response Time (ms)",
            "Training Block", "Timestamp"
            ]

            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            # Map old keys to new headers
            for trial in experimental_data:
                writer.writerow({
                    "Participant ID": trial['participant_id'],
                    "Version": trial['version'],
                    "Block N": trial['block_n'],
                    "Trial Index": trial['trial_index'],
                    "Stimulus Digit": trial['stimulus_digit'],
                    "Is Target": trial['is_target'],
                    "Response": trial['response'],
                    "Accuracy": trial['accuracy'],
                    "Reaction Time (ms)": trial['rt'],
                    "Stimulus Onset (ms)": trial['stimulus_onset'],
                    "Response Time (ms)": trial['response_time'],
                    "Training Block": trial['training'],
                    "Timestamp": trial['timestamp']
                })

        if DEBUG:
            print(f"Data saved to {filepath}")
    except Exception as e:
         messagebox.showerror("Save Error", f"Could not save data: {str(e)}\nTried path: {filepath}")
         return None
    return str(filepath)

def show_frame(frame):
    """Show the specified frame"""
    # Unbind keys when switching frames
    root.unbind('<Key>')
    
    # Hide all frames
    for f in [frame_csv_login, frame_pid_login, frame_experiment, 
             frame_transition, frame_end, frame_instruction_1, 
             frame_instruction_2, frame_instruction_3, frame_instruction_4]:
        f.pack_forget()
    
    # Show requested frame
    frame.pack(expand=True, fill='both')
    root.update_idletasks()
    
    # Set focus appropriately
    def set_focus():
        try:
            if frame == frame_csv_login:
                entry_first.focus_set()
                entry_first.select_range(0, tk.END)
            elif frame == frame_pid_login:
                entry_pid.focus_set()
                entry_pid.select_range(0, tk.END)
            elif frame == frame_experiment:
                root.focus_set()
            elif frame == frame_transition:
                btn_start_experiment.focus_set()
            elif frame in [frame_instruction_1, frame_instruction_2, frame_instruction_3, frame_instruction_4]:
                btn_next.focus_set()
        except Exception:
            pass
    
    root.after(50, set_focus)

def handle_csv_login():
    """Handle CSV-based login"""
    global participant_id, current_version, first_time_participant
    first = entry_first.get().strip().lower()
    last = entry_last.get().strip().lower()
    
    if DEBUG:
        print(f"Attempting login for: {first} {last}")
        print(f"Using CSV path: {CSV_PATH}")
        print(f"File exists: {os.path.exists(CSV_PATH)}")

    if not first or not last:
        lbl_csv_error.config(text="Please enter both names")
        return
    
    try:
        if not os.path.exists(CSV_PATH):
            lbl_csv_error.config(text="Error: sample_sheet.csv not found")
            return
        
        with open(CSV_PATH) as f:
            reader = csv.DictReader(f)
            participants = list(reader)
            
        if not participants or 'Participant' not in participants[0]:
            lbl_csv_error.config(text="Error: Invalid CSV format")
            return
            
        full_name = f"{first} {last}"
        participant = next((p for p in participants if p['Participant'].strip().lower() == full_name), None)
        
        if participant:
            participant_id = participant['Participant iD'].strip()
            completed = int(participant['Trial Number'].strip())
            current_version = completed + 1
            first_time_participant = (completed == 1)
            
            if current_version > 5:
                messagebox.showinfo("Complete", "You've finished all trials!")
                root.quit()
                return
                
            show_instructions()
        else:
            lbl_csv_error.config(text="Participant not found in sample_sheet.csv")
            
    except Exception as e:
        lbl_csv_error.config(text=f"Error: {str(e)}")
        if DEBUG:
            print(f"CSV Error: {str(e)}")

def handle_pid_login():
    """Handle PID-based login"""
    global participant_id, current_version, first_time_participant
    pid = entry_pid.get().strip()
    version = entry_version.get().strip()
    
    if not pid or not version:
        messagebox.showerror("Error", "Please fill all fields")
        return
    
    try:
        current_version = int(version)
        if current_version < 1 or current_version > 5:
            raise ValueError("Version must be between 1-5")
        participant_id = pid
        first_time_participant = (current_version == 1)  # Assume not first time for manual login
        show_instructions()
    except Exception as e:
        messagebox.showerror("Error", f"Invalid version: {str(e)}")

def on_return(event):
    """Handle Enter key press in login forms"""
    widget = root.focus_get()
    if widget in [entry_first, entry_last]:
        handle_csv_login()
    elif widget in [entry_pid, entry_version]:
        handle_pid_login()

def safe_button_click(command_func):
    """Decorator to prevent double-clicks on buttons"""
    def wrapper(*args, **kwargs):
        try:
            widget = root.focus_get()
            if hasattr(widget, 'config'):
                widget.config(state='disabled')
                root.after(100, lambda: widget.config(state='normal'))
            command_func()
        except Exception as e:
            if DEBUG:
                print(f"Button click error: {e}")
    return wrapper

def on_tab_key(event):
    """Handle tab navigation between fields"""
    if event.widget == entry_first:
        entry_last.focus_set()
        return "break"
    elif event.widget == entry_last:
        entry_first.focus_set()
        return "break"
    elif event.widget == entry_pid:
        entry_version.focus_set()
        return "break"
    elif event.widget == entry_version:
        entry_pid.focus_set()
        return "break"

def update_instruction_buttons():
    """Update instruction buttons based on participant status"""
    if first_time_participant:
        btn_skip.config(state="disabled")
        instruction_note.config(text="Training is mandatory for first-time participants", foreground="#ff9900")
    else:
        btn_skip.config(state="normal")
        instruction_note.config(text="You may skip training if you're familiar with the task", foreground="#ffffff")

def update_instruction_titles():
    """Update instruction titles with participant ID"""
    welcome_title.config(text=f"Welcome to the N-back experiment, Participant {participant_id}")
    training_title.config(text=f"Training Instructions - Participant {participant_id}")

def replay_speech():
    """Stop any ongoing speech and replay the current instruction."""
    if not engine:
        return
    try:
        engine.stop()                       
        speak(NARRATIONS[current_instruction_page])
    except Exception as e:
        if DEBUG:
            print(f"Replay error: {e}")

def show_instructions():
    """Show instruction screens"""
    global current_instruction_page
    current_instruction_page = 1
    update_instruction_titles()
    show_frame(frame_instruction_1)
    update_instruction_buttons()
    speak(NARRATIONS[1])

def next_instruction():
    """Show next instruction page"""
    global current_instruction_page
    current_instruction_page += 1
    if current_instruction_page == 1:
        show_frame(frame_instruction_1)
        speak(NARRATIONS[1])
    elif current_instruction_page == 2:
        show_frame(frame_instruction_2)
        speak(NARRATIONS[2])
    elif current_instruction_page == 3:
        show_frame(frame_instruction_3)
        speak(NARRATIONS[3])
    elif current_instruction_page == 4:
        show_frame(frame_instruction_4)
        speak(NARRATIONS[4])

def prev_instruction():
    """Show previous instruction page"""
    global current_instruction_page
    current_instruction_page -= 1
    if current_instruction_page == 1:
        show_frame(frame_instruction_1)
    elif current_instruction_page == 2:
        show_frame(frame_instruction_2)
    elif current_instruction_page == 3:
        show_frame(frame_instruction_3)
    elif current_instruction_page == 4:
        show_frame(frame_instruction_4)

def start_training():
    """Start training session with tutorial"""
    global trial_index, block_index
    trial_index = 0
    block_index = 0
    show_frame(frame_experiment)
    stimulus_label.config(text="Starting tutorial...", fg="white")
    instruction_label.config(text="")
    feedback_label.config(text="")
    root.update_idletasks()
    root.after(1500, run_tutorial_trial)

def skip_training():
    """Skip training if allowed"""
    if first_time_participant:
        messagebox.showwarning("Training Required", "Training is mandatory for first-time participants")
        return
        
    prepare_blocks(training=False)
    show_frame(frame_experiment)
    start_block()

def start_actual_experiment():
    """Start the main experiment"""
    prepare_blocks(training=False)
    show_frame(frame_experiment)
    start_block()

def confirm_exit():
    """Confirm before exiting the application"""
    if messagebox.askyesno("Quit", "Are you sure you want to exit?"):
        if engine:
            try:
                engine.stop()
            except Exception:
                pass
        root.destroy()

# --- UI Setup ---
root = tk.Tk()
root.title("N-Back Experiment")
root.attributes('-fullscreen', True)
root.configure(bg="#2d2d2d")
root.protocol("WM_DELETE_WINDOW", confirm_exit)
root.bind('<Escape>', lambda e: root.attributes('-fullscreen', False))

# Configure ttk styles
style = ttk.Style()
style.theme_use('clam')
style.configure('.', background="#2d2d2d", foreground="#ffffff")
style.configure('TFrame', background="#2d2d2d")
style.configure('TLabel', background="#2d2d2d", foreground="#ffffff", font=('Helvetica', 18))
style.configure('Title.TLabel', font=('Helvetica', 40, 'bold'))
style.configure('Example.TLabel', font=('Helvetica', 40, 'bold'))
style.configure('Instruction.TLabel', font=('Helvetica', 25), wraplength=800, justify='center')
style.configure('TButton', 
                font=('Helvetica', 25, 'bold'),
                background='#d9d9d9',
                padding=(20, 12),
                foreground='black',
                borderwidth=2)
style.map('TButton',
          background=[('active', '#0056b3')],
          relief=[('pressed', 'sunken'), ('!pressed', 'raised')])
style.configure('TEntry', 
                fieldbackground="#404040", 
                foreground="#ffffff",
                insertcolor="#ffffff",
                font=('Helvetica', 18),
                borderwidth=2)

# --- Frames ---
frame_csv_login = ttk.Frame(root)
frame_pid_login = ttk.Frame(root)
frame_experiment = ttk.Frame(root)
frame_transition = ttk.Frame(root)
frame_end = ttk.Frame(root)
frame_instruction_1 = ttk.Frame(root)
frame_instruction_2 = ttk.Frame(root)
frame_instruction_3 = ttk.Frame(root)
frame_instruction_4 = ttk.Frame(root)

# --- CSV Login Screen ---
csv_container = ttk.Frame(frame_csv_login)
csv_container.pack(expand=True, padx=30, pady=20)

ttk.Label(csv_container, text="N-Back Experiment", style='Title.TLabel').pack(pady=20)
ttk.Label(csv_container, text="Please enter your first and last name.").pack(pady=10)

form_frame = ttk.Frame(csv_container)
form_frame.pack(pady=8)

ttk.Label(form_frame, text="First Name:").grid(row=0, column=0, padx=10, pady=10, sticky='w')
entry_first = ttk.Entry(form_frame, width=25, font=('Helvetica', 18))
entry_first.grid(row=0, column=1, padx=10, pady=10, sticky='ew', ipady=8)

ttk.Label(form_frame, text="Last Name:").grid(row=1, column=0, padx=10, pady=10, sticky='w')
entry_last = ttk.Entry(form_frame, width=25, font=('Helvetica', 18))
entry_last.grid(row=1, column=1, padx=10, pady=10, sticky='ew', ipady=8)

form_frame.columnconfigure(1, weight=1)

entry_first.bind('<Tab>', on_tab_key)
entry_last.bind('<Tab>', on_tab_key)

lbl_csv_error = ttk.Label(csv_container, foreground="red")
lbl_csv_error.pack(pady=10)

btn_frame = ttk.Frame(csv_container)
btn_frame.pack(pady=8)

ttk.Button(btn_frame, text="Start", 
           command=safe_button_click(handle_csv_login)).pack(side='left', padx=10)
ttk.Button(btn_frame, text="Login with pID", 
           command=safe_button_click(lambda: show_frame(frame_pid_login))).pack(side='left', padx=10)

# --- PID Login Screen ---
pid_container = ttk.Frame(frame_pid_login)
pid_container.pack(expand=True, padx=40, pady=40)

ttk.Button(pid_container, text="← Back to Main Login", 
           command=safe_button_click(lambda: show_frame(frame_csv_login))).pack(pady=10, anchor='w')
ttk.Label(pid_container, text="Alternative Login", style='Title.TLabel').pack(pady=20)

# Updated instruction text for alternative login
ttk.Label(pid_container, 
          text="Enter your participant ID and the version number of the trial\n"
               "(1 if this is your first time, 2-5 for subsequent sessions).",
          style='Instruction.TLabel').pack(pady=10)

pid_form = ttk.Frame(pid_container)
pid_form.pack(pady=20)

ttk.Label(pid_form, text="Participant ID:").grid(row=0, column=0, padx=10, pady=10, sticky='w')
entry_pid = ttk.Entry(pid_form, width=25, font=('Helvetica', 18))
entry_pid.grid(row=0, column=1, padx=10, pady=10, sticky='ew', ipady=8)

ttk.Label(pid_form, text="Visit Number (1-5):").grid(row=1, column=0, padx=10, pady=10, sticky='w')
entry_version = ttk.Entry(pid_form, width=25, font=('Helvetica', 18))
entry_version.grid(row=1, column=1, padx=10, pady=10, sticky='ew', ipady=8)

pid_form.columnconfigure(1, weight=1)
entry_pid.bind('<Tab>', on_tab_key)
entry_version.bind('<Tab>', on_tab_key)

ttk.Button(pid_container, text="Start", 
           command=safe_button_click(handle_pid_login)).pack(pady=20)

# --- Instruction Frame 1: Welcome Screen ---
inst_container_1 = ttk.Frame(frame_instruction_1)
inst_container_1.pack(expand=True, padx=40, pady=40)

welcome_title = ttk.Label(inst_container_1, style='Title.TLabel')
welcome_title.pack(pady=10)

ttk.Label(inst_container_1, 
          text="In this task, numbers will be presented on the screen one at a time. "
               "\n\nPay attention to the numbers, and if the number on the screen is the same "
               "as the number N times before, press the spacebar. \n\nClick the button to view examples and begin the tutorial.",
          style='Instruction.TLabel').pack(pady=20, padx=20)

nav_frame_1 = ttk.Frame(inst_container_1)
nav_frame_1.pack(pady=30)
ttk.Button(nav_frame_1, text="🔊 Replay Speech",
           command=safe_button_click(replay_speech)).pack(side='left', padx=10)
btn_next = ttk.Button(nav_frame_1, text="Next →", command=safe_button_click(next_instruction))
btn_next.pack(side='right', padx=10)

# --- Instruction Frame 2: 1-back Example ---
inst_container_2 = ttk.Frame(frame_instruction_2)
inst_container_2.pack(expand=True, padx=40, pady=40)

ttk.Label(inst_container_2, text="1-back Example", style='Title.TLabel').pack(pady=20)
ttk.Label(inst_container_2, 
          text="Press SPACEBAR when the number is the same as the previous number:",
          style='Instruction.TLabel').pack(pady=10)

example_frame_2 = ttk.Frame(inst_container_2)
example_frame_2.pack(pady=20)
ttk.Label(example_frame_2, text="5", style='Example.TLabel').pack(side='left', padx=15)
ttk.Label(example_frame_2, text="3", style='Example.TLabel').pack(side='left', padx=15)
ttk.Label(example_frame_2, text="3", style='Example.TLabel', foreground="#ff9900").pack(side='left', padx=15)
ttk.Label(example_frame_2, text="→ Press SPACE here", style='Instruction.TLabel').pack(side='left', padx=15)

ttk.Label(inst_container_2, 
          text="In this example, press SPACE on the third number because it matches the previous number.",
          style='Instruction.TLabel').pack(pady=10)

nav_frame_2 = ttk.Frame(inst_container_2)
nav_frame_2.pack(pady=30)
ttk.Button(nav_frame_2, text="🔊 Replay Speech",
           command=safe_button_click(replay_speech)).pack(side='left', padx=10)
ttk.Button(nav_frame_2, text="← Back", 
           command=safe_button_click(prev_instruction)).pack(side='left', padx=10)
ttk.Button(nav_frame_2, text="Next →", 
           command=safe_button_click(next_instruction)).pack(side='right', padx=10)

# --- Instruction Frame 3: 2-back Example ---
inst_container_3 = ttk.Frame(frame_instruction_3)
inst_container_3.pack(expand=True, padx=40, pady=40)

ttk.Label(inst_container_3, text="2-back Example", style='Title.TLabel').pack(pady=20)
ttk.Label(inst_container_3, 
          text="Press SPACEBAR when the number is the same as the number shown two numbers ago:",
          style='Instruction.TLabel').pack(pady=10)

example_frame_3 = ttk.Frame(inst_container_3)
example_frame_3.pack(pady=20)
ttk.Label(example_frame_3, text="5", style='Example.TLabel').pack(side='left', padx=15)
ttk.Label(example_frame_3, text="3", style='Example.TLabel').pack(side='left', padx=15)
ttk.Label(example_frame_3, text="5", style='Example.TLabel', foreground="#ff9900").pack(side='left', padx=15)
ttk.Label(example_frame_3, text="→ Press SPACE here", style='Instruction.TLabel').pack(side='left', padx=15)

ttk.Label(inst_container_3, 
          text="In this example, press SPACE on the third number because it matches \nthe number two positions back.",
          style='Instruction.TLabel').pack(pady=10)

nav_frame_3 = ttk.Frame(inst_container_3)
nav_frame_3.pack(pady=30)
ttk.Button(nav_frame_3, text="🔊 Replay Speech",
           command=safe_button_click(replay_speech)).pack(side='left', padx=10)
ttk.Button(nav_frame_3, text="← Back", 
           command=safe_button_click(prev_instruction)).pack(side='left', padx=10)
ttk.Button(nav_frame_3, text="Next →", 
           command=safe_button_click(next_instruction)).pack(side='right', padx=10)

# --- Instruction Frame 4: Training Instructions ---
inst_container_4 = ttk.Frame(frame_instruction_4)
inst_container_4.pack(expand=True, padx=40, pady=40)

training_title = ttk.Label(inst_container_4, style='Title.TLabel')
training_title.pack(pady=20)

ttk.Label(inst_container_4, 
          text="For the tutorial, you will be doing 1-back and 2-back tasks to practice before the main experiment. "
               "During the tutorial, you'll get immediate feedback on your responses.",
          style='Instruction.TLabel').pack(pady=10, padx=20)

ttk.Label(inst_container_4, 
          text="The tutorial will show 6 trials for each task (1-back and 2-back) with a mix of targets and non-targets. "
               "After each response, you'll see if you were correct and get an explanation.",
          style='Instruction.TLabel').pack(pady=10, padx=20)

ttk.Label(inst_container_4, 
          text="Remember: Press SPACE only if the number matches the one shown N positions back!",
          style='Instruction.TLabel', foreground="#ff9900").pack(pady=10, padx=20)

ttk.Label(inst_container_4, 
          text="When you are ready, press 'Start Training' to begin. "
               "If you are already familiar with the task, you can press 'Skip Training' to proceed directly to the main experiment.",
          style='Instruction.TLabel').pack(pady=10, padx=20)

instruction_note = ttk.Label(inst_container_4, 
                             text="", 
                             style='Instruction.TLabel',
                             foreground="#ff9900")
instruction_note.pack(pady=10, padx=20)

btn_train_frame = ttk.Frame(inst_container_4)
btn_train_frame.pack(pady=30)
ttk.Button(btn_train_frame, text="🔊 Replay Speech",
           command=safe_button_click(replay_speech)).pack(side='left', padx=10)
ttk.Button(btn_train_frame, text="← Back", 
           command=safe_button_click(prev_instruction)).pack(side='left', padx=10)
btn_skip = ttk.Button(btn_train_frame, text="Skip Training", 
                      command=safe_button_click(skip_training))
btn_skip.pack(side='left', padx=10)
ttk.Button(btn_train_frame, text="Start Training", 
           command=safe_button_click(start_training)).pack(side='left', padx=10)

# --- Experiment Frame ---
experiment_container = ttk.Frame(frame_experiment)
experiment_container.pack(expand=True, fill='both')

# Add instruction label (only used in tutorial)
instruction_label = ttk.Label(experiment_container, 
                            text="", 
                            font=("Helvetica", 35),
                            foreground="#ffffff",
                            background="#2d2d2d",
                            anchor='center')
instruction_label.pack(pady=20)

stimulus_label = tk.Label(experiment_container, 
                          text="", 
                          font=("Helvetica", 144, "bold"),
                          fg="#ffffff",
                          bg="#2d2d2d")
stimulus_label.pack(expand=True)

# Add feedback label for tutorial
feedback_label = ttk.Label(experiment_container, 
                          text="", 
                          font=("Helvetica", 35),
                          foreground="#ffffff",
                          background="#2d2d2d",
                          anchor='center')
feedback_label.pack(pady=20)

# --- Transition Frame ---
transition_container = ttk.Frame(frame_transition)
transition_container.pack(expand=True, padx=40, pady=40)

ttk.Label(transition_container, text="Training Complete!", style='Title.TLabel').pack(pady=30)
ttk.Label(transition_container,
          text="Great job! You've finished the training phase.\n\n"
               "Now you'll complete the actual experiment with the same tasks.\n"
               "It is important to note that in the actual experiment, you will not know if your answers are correct, and the stimuli will be much quicker.\n"
               "Remember: Press SPACEBAR when the digit matches the one from N positions back.",
          wraplength=600,
          justify='center',
          font=("Helvetica", 25)).pack(pady=30)

# Create a frame for buttons to arrange them vertically
button_container = ttk.Frame(transition_container)
button_container.pack(pady=20)

# Button to start experiment
btn_start_experiment = ttk.Button(button_container, 
                                 text="Start Experiment", 
                                 command=safe_button_click(start_actual_experiment))
btn_start_experiment.pack(pady=10)

# Button to redo tutorial
btn_redo_tutorial = ttk.Button(button_container, 
                               text="Redo Tutorial", 
                               command=safe_button_click(redo_tutorial))
btn_redo_tutorial.pack(pady=10)

# --- End Frame ---
end_container = ttk.Frame(frame_end)
end_container.pack(expand=True, padx=40, pady=40)

ttk.Label(end_container, text="Thank you for your participation!", style='Title.TLabel').pack(pady=30)
ttk.Label(end_container,
          text=f"Your data has been automatically saved!",
          wraplength=600,
          justify='center',
          font=("Helvetica", 16)).pack(pady=20)

# --- Initialize ---
show_frame(frame_csv_login)
root.mainloop()