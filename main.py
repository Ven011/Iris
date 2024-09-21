#!/usr/bin/python3

import cv2
import tkinter as tk
import numpy as np

from cupid import Cupid
from PIL import Image, ImageTk
from settings import get_setting
from datetime import datetime
from time import time
from email_sender import send_email

cupid = Cupid()

# interface variables
date_count = 0
date_weight = 0
interface_closed = False
started = False
operation_start = 0
operation_end = 0

# user variables
DATE_REPORT_FREQ = 50 # milliseconds between consecutive date reports
COUNT_WEIGHT_FREQ = 200 # milliseconds between date count and weight text in the main menu

# setup tkinter
root = tk.Tk()
root.attributes("-fullscreen", True)
root.title("Date Counter and Weight Estimator")

# main menu holder
main_holder = tk.Label(root)

main_holder.pack(fill="both", expand=True)

for i in range(3):
    main_holder.grid_columnconfigure(i, weight=1, uniform="equal")

main_holder.grid_rowconfigure(0, weight=1)
main_holder.grid_rowconfigure(1, weight=1)
main_holder.grid_rowconfigure(2, weight=1)

# image holder
image_label = tk.Label(main_holder, borderwidth=2, relief="solid", text="CAMERA VIEW", compound="bottom", font=("Helvetica", 20, "bold"))
image_label.grid(row=0, column=2, rowspan=3, sticky="nsew" , padx=20, pady=20)

# count and weight text widgets
count_label = tk.Label(main_holder, font=("Helvetica", 25, "bold"), borderwidth=2, relief="solid")
weight_label = tk.Label(main_holder, font=("Helvetica", 25, "bold"), borderwidth=2, relief="solid")

count_label.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=20, pady=20)
weight_label.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=20, pady=20)

def handle_start():
    global started, operation_start
    operation_start = time()
    started = True if not started else started

def handle_stop():
    global started, operation_end
    cupid.reset()
    operation_end = time()
    # send email with date count, total weight, count start and end times
    subject = "Date Counter Report"
    date_and_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    body = f"Operation date and end time: {date_and_time}, Dates counted: {date_count}, Estimated total weight: {round(date_weight/1000, 4)} kg"
    
    # send email to recipients
    send_email(subject, body, get_setting("email_settings")["recipient1_email"])
    send_email(subject, body, get_setting("email_settings")["recipient2_email"])

    started = False if started else started

# main menu buttons
start_button = tk.Button(main_holder, text="START", bg="green", font=("Helvetica", 30, "bold"),
                         command=handle_start)
stop_button = tk.Button(main_holder, text="STOP", bg="red", font=("Helvetica", 30, "bold"),
                        command=handle_stop)

start_button.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
stop_button.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

def get_date_report():
    global date_count, date_weight
    if started:
        date_count, date_weight, date_frame = cupid.work()
        # convert date frame to tkinter image
        rgb_frame = cv2.cvtColor(date_frame, cv2.COLOR_BGR2RGB)
        rgb_frame = cv2.resize(rgb_frame, (200, 200))
        pil_frame = Image.fromarray(rgb_frame)
        tk_frame = ImageTk.PhotoImage(image=pil_frame)
        # show image
        image_label.config(image=tk_frame)
        image_label.image = tk_frame
        root.after(DATE_REPORT_FREQ, get_date_report)
    else:
        pil_frame = Image.fromarray(np.zeros((200, 200), dtype=np.uint8))
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

root.bind("q", close_interface)
root.bind("f", exit_fullscreen)

root.after(DATE_REPORT_FREQ, get_date_report)
root.after(COUNT_WEIGHT_FREQ, update_count_weight)

root.mainloop()


