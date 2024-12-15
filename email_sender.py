#!/usr/bin/python3

import smtplib
import threading

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Email configuration
smtp_server = "smtp.gmail.com"  # Replace with your SMTP server
smtp_port = 587  # Use 465 for SSL, 587 for TLS
sender_email = "datecounter0@gmail.com"
password = "brtujkkhgirenane"

class Email_sender:
    def __init__(self):
        self.email_subject = None
        self.email_body = None
        self.email_recipients = None

    def start_emailing(self):
        if self.email_subject and self.email_body and self.email_recipients:
            email_send_thread = threading.Thread(target=self.send_email)
            email_send_thread.start()

    def send_email(self): 
        for recipient in self.email_recipients:   
            # Setup the MIME
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = recipient
            msg['Subject'] = self.email_subject

            # Attach the body with the msg instance
            msg.attach(MIMEText(self.email_body, 'plain'))

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

sender = Email_sender()