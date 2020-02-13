from email.mime.image import MIMEImage


def send_mail(msg_to_send, subject):
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    import smtplib
    # configuraciones generales:
    SERVER = "mail.cenace.org.ec"


    # create message object instance
    msg = MIMEMultipart('related')

    # setup the parameters of the message
    # password = "cenace.123"
    recipients = ["cdhierro@cenace.org.ec"]
    msg['From'] = "sistemaremoto@cenace.org.ec"
    msg['To'] = ", ".join(recipients)
    msg['Subject'] = subject
    msg.preamble = """"""


    HTML_BODY = MIMEText(msg_to_send, 'html')
    msg.attach(HTML_BODY)

    # add in the message body
    # msg.attach(MIMEText(message, 'plain'))

    # This example assumes the image is in templates
    fp = open('templates/cenace.jpg', 'rb')
    msgImage = MIMEImage(fp.read())
    fp.close()

    # Define the image's ID as referenced above
    msgImage.add_header('Content-ID', '<image1>')
    msg.attach(msgImage)

    # create server
    server = smtplib.SMTP(SERVER)

    server.starttls()

    # Login Credentials for sending the mail
    # server.login(msg['From'], password)

    # send the message via the server.
    server.sendmail(msg['From'], recipients, msg.as_string())

    server.quit()

    print("Detalles enviados a: %s:" % (msg['To']))

