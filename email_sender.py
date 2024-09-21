#!/usr/bin/python3

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from settings import get_setting

# Email configuration
smtp_server = "smtp.gmail.com"  # Replace with your SMTP server
smtp_port = 587  # Use 465 for SSL, 587 for TLS
sender_email = "datecounter0@gmail.com"
password = "brtujkkhgirenane"

def send_email(subject, body, recipient):    
    # Setup the MIME
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient
    msg['Subject'] = subject

    # Attach the body with the msg instance
    msg.attach(MIMEText(body, 'plain'))

    try:
        # Start the server and login
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # Secure the connection
        server.login(sender_email, password)
        
        # Send the email
        text = msg.as_string()
        server.sendmail(sender_email, recipient, text)
        
        print("Email sent successfully!")
        server.quit()
        
    except Exception as e:
        print(f"Email Error: {e}")