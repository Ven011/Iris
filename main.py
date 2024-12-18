#!/usr/bin/python3

import cv2
import tkinter as tk
import numpy as np
import json

from tkinter import messagebox
from cupid import Cupid
from PIL import Image, ImageTk
from settings import settings
from datetime import datetime
from time import time
from email_sender import sender

cupid = Cupid()

# interface variables
date_count = 0
date_weight = 0
interface_closed = False
started = False
operation_start = 0
operation_end = 0

DATE_REPORT_FREQ = 10 # milliseconds between consecutive date reports
COUNT_WEIGHT_FREQ = 200 # milliseconds between date count and weight text in the main menu

# setup tkinter
root = tk.Tk()
root.attributes("-fullscreen", True)
# root.geometry("1920x1080")
root.title("Date Counter and Weight Estimator")

# main menu ------------------------------------------------------------------------
main_holder = tk.Frame(root)
main_holder.pack(fill="both", expand=True)

for i in range(3): 
    main_holder.grid_columnconfigure(i, weight=1, uniform="equal")

main_holder.grid_rowconfigure(0, weight=1)
main_holder.grid_rowconfigure(1, weight=1)
main_holder.grid_rowconfigure(2, weight=1)

# image holder
image_label = tk.Label(main_holder, borderwidth=2, relief="solid", text="CAMERA VIEW", compound="bottom", font=("Helvetica", 20, "bold"))
image_label.grid(row=1, column=2, rowspan=2, sticky="nsew" , padx=20, pady=20)

# count and weight text widgets
count_label = tk.Label(main_holder, font=("Helvetica", 25, "bold"), borderwidth=2, relief="solid")
weight_label = tk.Label(main_holder, font=("Helvetica", 25, "bold"), borderwidth=2, relief="solid")

count_label.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=20, pady=20)
weight_label.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=20, pady=20)

# settings widgets 
settings_holder = tk.Label(main_holder)
settings_holder.grid(row=0, column=2, sticky="nsew", columnspan=1, padx=20, pady=20)

settings_holder.grid_columnconfigure(0, weight=1, uniform="equal")
settings_holder.grid_rowconfigure(0, weight=1, uniform="equal")

# wifi_status = tk.Label(settings_holder, borderwidth=2, relief="solid", text="WiFi STATUS", font=("Helvetica", 15, "bold"))
# camera_status = tk.Label(settings_holder, borderwidth=2, relief="solid", text="CAMERA STATUS", font=("Helvetica", 15, "bold"))

# wifi_status.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
# camera_status.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

password_keypad = tk.Frame(root, background="gray", padx=20, pady=20)

# settings menu ------------------------------------------------------------------------
in_settings = False
settings_menu_holder = tk.Frame(root)

settings.settings = {
    "count_line_offset": {"value": tk.IntVar(value=0), "limits": [0, 200], "tick": 10, "factor": 1},
    "weight_estimation_m": {"value": tk.DoubleVar(value=0), "limits": [0, 200], "tick": 20, "factor": 0.0001}, # actual range: divide limits by 10,000
    "weight_estimation_b": {"value": tk.DoubleVar(value=0), "limits": [0, 200], "tick": 20, "factor": 0.01}, # divide limits by 100
    "match_distance": {"value": tk.IntVar(value=0), "limits": [0, 100], "tick": 10, "factor": 1},
    "match_percent": {"value": tk.DoubleVar(value=0), "limits": [0, 100], "tick": 10, "factor": 0.01}, # divide limits by 100
    "base_profile_translation": {"value": tk.IntVar(value=0), "limits": [0, 20], "tick": 2, "factor": 1},
    "match_attempts": {"value": tk.IntVar(value=0), "limits": [0, 10], "tick": 1, "factor": 1}
}

# get setting values from settings file
settings.fetch_counter_settings()

for i in range(3): settings_menu_holder.grid_columnconfigure(i, weight=1)
for i in range(12): settings_menu_holder.grid_rowconfigure(i, weight=1)

# camera preview
camera_preview_holder = tk.Frame(settings_menu_holder)
camera_preview_holder.grid(row=0, column=2, columnspan=1, rowspan=5, sticky="nsew")
camera_preview = tk.Label(camera_preview_holder, borderwidth=0, relief="solid", text="CAMERA PREVIEW", compound="bottom", font=("Helvetica", 20, "bold"))
camera_preview.pack(fill="both", expand=True)

# scales/ sliders for the settings
scales = []
for setting in settings.settings:
    setting_dict = settings.settings[setting]
    scale = tk.Scale(settings_menu_holder, label=setting, variable=setting_dict["value"],
                     from_=setting_dict["limits"][0], to=setting_dict["limits"][1], tickinterval=setting_dict["tick"],
                     orient=tk.HORIZONTAL)
    scales.append(scale)
    scale.grid(row=list(settings.settings).index(setting)+1, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)

# password setting text box
password_setting_holder = tk.Frame(settings_menu_holder)
password_setting_holder.grid(row=5, column=2, rowspan=1, sticky="nsew")
for i in range(8): password_setting_holder.grid_columnconfigure(i, weight=1)
password_setting_holder.grid_rowconfigure(0, weight=1)

password_setting_label = tk.Label(password_setting_holder, text="Settings Password (4 numbers, 1-9 only):")
password_setting_label.grid(column=1, row=0, columnspan=1, sticky="nse")
password_setting_entry = tk.Text(password_setting_holder, height=1, width=5)
password_setting_entry.grid(column=2, row=0, columnspan=2, sticky="ew")

# email setting text box
email_setting_holder = tk.Frame(settings_menu_holder)
email_setting_holder.grid(row=6, column=2, rowspan=1, sticky="nsew")
for i in range(8): email_setting_holder.grid_columnconfigure(i, weight=1)
email_setting_holder.grid_rowconfigure(0, weight=1)

email_setting_label = tk.Label(email_setting_holder, text="Emails :")
email_setting_label.grid(column=1, row=0, columnspan=1, sticky="nse")
email1 = tk.Text(email_setting_holder, height=1, width=5)
email2 = tk.Text(email_setting_holder, height=1, width=5)
email1.grid(column=2, row=0, columnspan=2, sticky="ew")
email2.grid(column=4, row=0, columnspan=2, sticky="ew")

# # wifi setting text boxes
# wifi_setting_holder = tk.Frame(settings_menu_holder)
# wifi_setting_holder.grid(row=7, column=2, rowspan=2, sticky="nsew")
# for i in range(8): wifi_setting_holder.grid_columnconfigure(i, weight=1)
# for i in range(2): wifi_setting_holder.grid_rowconfigure(i, weight=1)

# wifi_ssid_label = tk.Label(wifi_setting_holder, text="WiFi SSID:")
# wifi_pass_label = tk.Label(wifi_setting_holder, text="WiFi Password:")
# wifi_ssid_label.grid(column=1, row=0, columnspan=1, sticky="nse")
# wifi_pass_label.grid(column=1, row=1, columnspan=1, sticky="nse")
# wifi_ssid_entry = tk.Text(wifi_setting_holder, height=1, width=5)
# wifi_pass_entry = tk.Text(wifi_setting_holder, height=1, width=5)
# wifi_ssid_entry.grid(column=2, row=0, columnspan=3, sticky="ew")
# wifi_pass_entry.grid(column=2, row=1, columnspan=3, sticky="ew")

settings.fetch_network_settings()

# ---------------------------------------------------------------------------------------

def update_network_settings():
    ns = settings.network_settings

    password_setting_entry.replace("1.0", "end", ns["settings_password"])
    email1.replace("1.0", "end", ns["recipient1_email"])
    email2.replace("1.0", "end", ns["recipient2_email"])
    # wifi_ssid_entry.replace("1.0", "end", ns["wifi_ssid"])
    # wifi_pass_entry.replace("1.0", "end", ns["wifi_password"])

def handle_start():
    global started, operation_start
    operation_start = time()
    
    #notify
    if started and cupid.camera_connected():
        messagebox.showinfo("Error", "Operation Already Started!")
    elif not started and cupid.camera_connected():
        started = True
        messagebox.showinfo("Success", "Starting Operation!")
    else:
        messagebox.showinfo("Error", "Camera Not Connected!")
        messagebox.showinfo("", "Attempting Camera Reconnect...")
        cupid.attempt_camera_reconnect()

def handle_stop():
    global started, operation_end, date_count, date_weight
    
    #notify
    if not started and cupid.camera_connected():
        messagebox.showinfo("Error", "Operation Has Not Been Started!")
    elif started and cupid.camera_connected():
        started = False
        messagebox.showinfo("Success", "Ending Operation!")
        
        cupid.reset()
        operation_end = time()
    
        # send email with date count, total weight, count start and end times
        subject = "Date Counter Report"
        date_and_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        body = f"Operation date and end time: {date_and_time}, Dates counted: {date_count}, Estimated total weight: {round(date_weight/1000, 4)} kg"
        
        # send email to recipients
        sender.email_body = body
        sender.email_subject = subject
        sender.email_recipients = [settings.network_settings[f"recipient{num}_email"] for num in range(1,3)]
        sender.start_emailing()
        
        # reset count and weight on display
        date_count = 0
        date_weight = 0
        update_count_weight()
    else:
        messagebox.showinfo("Error", "Camera Not Connected!")

def to_settings():
    global in_settings

    in_settings = True
    # forget main menu
    main_holder.pack_forget()
    # update network settings values
    update_network_settings()
    # place settings menu
    settings_menu_holder.pack(fill="both", expand=True)

def to_main():
    global in_settings

    in_settings = False
    # forget the settings menu
    settings_menu_holder.pack_forget()
    # place the main menu
    main_holder.pack(fill="both", expand=True)

def show_keypad():
    # place keypad in root
    password_keypad.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

    # State to keep track of the entered code
    entered_code = tk.StringVar(value="")

    # Function to update the entered code
    def add_digit(digit):
        if len(entered_code.get()) < 4:
            entered_code.set(entered_code.get() + str(digit))

    # Function to check the password
    def check_password():
        if entered_code.get() == settings.network_settings["settings_password"]:
            messagebox.showinfo("Success", "Correct Password!")
            password_keypad.place_forget()
            for widget in password_keypad.winfo_children():
                widget.destroy()
            # go to settings menu
            to_settings()
        else:
            messagebox.showerror("Error", "Incorrect Password!")
            entered_code.set("")

    # Function to clear the last digit
    def delete_last():
        entered_code.set(entered_code.get()[:-1])

    # Function to close the keypad
    def close_keypad():
        password_keypad.place_forget()
        for widget in password_keypad.winfo_children():
            widget.destroy()

    # Create a label to display the entered code
    display = tk.Label(password_keypad, textvariable=entered_code, font=("Helvetica", 24), bg="lightgray", width=10, height=2)
    display.grid(row=0, column=0, columnspan=3, pady=10)

    # Add digit buttons
    for i in range(1, 10):
        button = tk.Button(password_keypad, text=str(i), font=("Helvetica", 18), width=4, height=2,
                           command=lambda digit=i: add_digit(digit))
        row = (i - 1) // 3 + 1
        col = (i - 1) % 3
        button.grid(row=row, column=col, padx=5, pady=5)

    # Add a back button to clear the last digit
    back_button = tk.Button(password_keypad, text="←", font=("Helvetica", 18), width=4, height=2, command=delete_last)
    back_button.grid(row=4, column=0, padx=5, pady=5)

    # Add a check button to verify the code
    check_button = tk.Button(password_keypad, text="OK", font=("Helvetica", 18), width=4, height=2, command=check_password)
    check_button.grid(row=4, column=1, padx=5, pady=5)

    # Add a close button to exit the keypad
    close_button = tk.Button(password_keypad, text="Close", font=("Helvetica", 18), width=4, height=2, command=close_keypad)
    close_button.grid(row=4, column=2, padx=5, pady=5)

def handle_settings():
    # ask user to enter password
    show_keypad()

def save_settings():
    # write counter setting values to the settings json file
    settings.save_counter_settings()
    # write network settings values to the network settings json file
    ns = settings.network_settings

    ns["settings_password"] = password_setting_entry.get("1.0", "end-1c")
    ns["recipient1_email"] = email1.get("1.0", "end-1c")
    ns["recipient2_email"] = email2.get("1.0", "end-1c")
    # ns["wifi_ssid"] = wifi_ssid_entry.get("1.0", "end-1c")
    # ns["wifi_password"] = wifi_pass_entry.get("1.0", "end-1c")

    with open("/home/datecounter/Iris/network_settings.json", "w") as setting_file:
        json.dump(ns, setting_file, indent=4)

    # return to main menu
    to_main()

def handle_camera_disconnect():
    global started

    if not cupid.camera_connected():
        started = False
        messagebox.showinfo("Error", "Camera Disconnected!")


def get_date_report():
    global date_count, date_weight
    # handle camera disconnect
    handle_camera_disconnect()

    if started or in_settings:
        init_t = time()
        date_count, date_weight, date_frame = cupid.work()
        print(time() - init_t)
        # convert date frame to tkinter image
        rgb_frame = cv2.cvtColor(date_frame, cv2.COLOR_BGR2RGB)
        rgb_frame = cv2.resize(rgb_frame, (400, 400))
        pil_frame = Image.fromarray(rgb_frame)
        tk_frame = ImageTk.PhotoImage(image=pil_frame)
        # show image
        if in_settings:
            camera_preview.config(image=tk_frame)
            camera_preview.image = tk_frame
        else:
            image_label.config(image=tk_frame)
            image_label.image = tk_frame
        root.after(DATE_REPORT_FREQ, get_date_report)

    else:
        pil_frame = Image.fromarray(np.zeros((400, 400), dtype=np.uint8))
        tk_frame = ImageTk.PhotoImage(image=pil_frame)
        # show image
        image_label.config(image=tk_frame)
        image_label.image = tk_frame
        root.after(DATE_REPORT_FREQ, get_date_report)

def update_count_weight():
    count_text = "COUNT: " + str(float(date_count)) + " dates"
    weight_text = "WEIGHT: " + str(round(float(date_weight/1000), 2)) + " kg"
    count_label.config(text = count_text)
    weight_label.config(text = weight_text)

    root.after(COUNT_WEIGHT_FREQ, update_count_weight)

def close_interface(event):
    cupid.stop()
    quit()

def exit_fullscreen(event):
    root.attributes("-fullscreen", False)

# main menu buttons
start_button = tk.Button(main_holder, text="START", bg="green", font=("Helvetica", 30, "bold"),
                        command=handle_start)
stop_button = tk.Button(main_holder, text="STOP", bg="red", font=("Helvetica", 30, "bold"),
                        command=handle_stop)
settings_button = tk.Button(settings_holder, text="SETTINGS", bg="gray", font=("Helvetica", 25, "bold"),
                        command=handle_settings)

# settings menu buttons
save_settings_button = tk.Button(settings_menu_holder, text="SAVE", bg="green", font=("Helvetica", 20, "bold"), command=save_settings)

start_button.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
stop_button.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
settings_button.grid(row=0, column=0, columnspan=1, sticky="nsew")
save_settings_button.grid(row=9, column=2, rowspan=2, ipadx=60, ipady=30)

root.bind("=", close_interface)
root.bind("-", exit_fullscreen)

root.after(DATE_REPORT_FREQ, get_date_report)
root.after(COUNT_WEIGHT_FREQ, update_count_weight)

root.mainloop()


