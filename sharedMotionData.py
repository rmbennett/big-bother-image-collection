#!/usr/bin/python
#****                                                                                         
# *** Motion Detection is based on the following ****  
#https://raw.githubusercontent.com/RobinDavid/Motion-detection-OpenCV/master/MotionDetector.py
#*****
#*****
#

import cv2.cv as cv
import cv2
from datetime import datetime
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText  # Added
from email.mime.image import MIMEImage
import smtplib
from threading import Thread
import os
# import mongoLABhelper
# from pymongo import MongoClient
# import rospy

class MotionDetectorInstantaneous():
    
    def onChange(self, val): #callback when the user change the detection threshold
        self.threshold = val
    
    def __init__(self,threshold=20, doRecord=True, showWindows=True):
        self.writer = None
        self.font = None
        self.doRecord=doRecord #Either or not record the moving object
        self.show = showWindows #Either or not show the 2 windows
        self.frame = None

        # Initiate mongodb connections
        # self.MotionCollection = mongoLABhelper.startMotionDatabaseURI("MotionCollection", "uri:port")
        # self.AlertCollection = mongoLABhelper.startAlertDatabaseURI("AlertCollection", "uri:port")

        self.capture=cv.CaptureFromCAM(0)
        self.frame = cv.QueryFrame(self.capture) #Take a frame to init recorder

        
        self.frame1gray = cv.CreateMat(self.frame.height, self.frame.width, cv.CV_8U) #Gray frame at t-1
        cv.CvtColor(self.frame, self.frame1gray, cv.CV_RGB2GRAY)
        
        #Will hold the thresholded result
        self.res = cv.CreateMat(self.frame.height, self.frame.width, cv.CV_8U)
        
        self.frame2gray = cv.CreateMat(self.frame.height, self.frame.width, cv.CV_8U) #Gray frame at t
        
        self.width = self.frame.width
        self.height = self.frame.height
        self.nb_pixels = self.width * self.height
        self.threshold = threshold
        self.isRecording = False
        self.trigger_time = 0 #Hold timestamp of the last detection
        
        if showWindows:
            cv.NamedWindow("Image")
            cv.CreateTrackbar("Detection threshold: ", "Image", self.threshold, 100, self.onChange)
        
    def initRecorder(self): #Create the recorder
        codec = cv.CV_FOURCC('M', 'J', 'P', 'G') #('W', 'M', 'V', '2')
        self.writer=cv.CreateVideoWriter(datetime.now().strftime("%b-%d_%H:%M:%S")+".wmv", codec, 20, cv.GetSize(self.frame), 1)
        #FPS set to 20 because it seems to be the fps of my cam but should be ajusted to your needs
        self.font = cv.InitFont(cv.CV_FONT_HERSHEY_SIMPLEX, 1, 1, 0, 2, 8) #Creates a font

    def send_async_email(self, attachment):

        # Define these once; use them twice!
        strFrom = 'example@example.com'
        strTo = 'example@example.com'

        # Create the root message and fill in the from, to, and subject headers
        msgRoot = MIMEMultipart('related')
        msgRoot['Subject'] = 'Motion message'
        msgRoot['From'] = strFrom
        msgRoot['To'] = strTo
        msgRoot.preamble = 'This is a multi-part message in MIME format.'

        # Encapsulate the plain and HTML versions of the message body in an
        # 'alternative' part, so message agents can decide which they want to display.
        msgAlternative = MIMEMultipart('alternative')
        msgRoot.attach(msgAlternative)

        msgText = MIMEText('This is the alternative plain text message.')
        msgAlternative.attach(msgText)

        # We reference the image in the IMG SRC attribute by the ID we give it below
        msgText = MIMEText('<b>It appears that there is a <i>person</i> nearby! Here is the image.<br><img src="cid:image1"><br>Regards, Motion Detection Software!', 'html')
        msgAlternative.attach(msgText)

        # This example assumes the image is in the current directory
        fp = open(attachment, 'rb')
        msgImage = MIMEImage(fp.read())
        fp.close()

        # Define the image's ID as referenced above
        msgImage.add_header('Content-ID', '<image1>')
        msgRoot.attach(msgImage)

        # Credentials (if needed)
        username = 'example'
        password = 'example'

        # Send the email (this example assumes SMTP authentication is required)
        smtp = smtplib.SMTP()

        smtp.connect('smtp.gmail.com:587') #example smtp connection
        smtp.ehlo()
        smtp.starttls()
        smtp.login(username, password)
        smtp.sendmail(strFrom, strTo, msgRoot.as_string())
        smtp.quit()

        os.remove(attachment)

    def motion_mongo_record(self, data, imagename):
        try:
            motion_id = mongoLABhelper.addMotionData(self.MotionCollection, data, imagename)
            print motion_id
            #print collection.find_one(motion_id)
        except:
            print "Error"
   
    def run(self):
        started = time.time()
        while True:
            
            curframe = cv.QueryFrame(self.capture)
            instant = time.time() #Get timestamp to the frame
            
            self.processImage(curframe) #Process the image
            
            if not self.isRecording:
                if self.somethingHasMoved():
                    self.trigger_time = instant #Update the trigger_time
                    if instant > started +5:#Wait 5 second after the webcam start for luminosity adjusting etc..
                        print datetime.now().strftime("%b %d, %H:%M:%S"), "Something is moving !"
                        if self.doRecord: #set isRecording=True only if we record a video
                            self.isRecording = True
                            ImageName = "motionDetected"+datetime.now().strftime("%b %d, %H:%M:%S")+".jpg"
                            cv.SaveImage(ImageName, curframe)
                            # send email and add data to the database
                            # thr = Thread(target = self.send_async_email, args =[ImageName])
                            # thr.start()
                            # mongoLABhelper.addAlertData(self.AlertCollection, "Motion Detected Alert!")
                            # self.motion_mongo_record(ImageName,ImageName)

            else:
                if instant >= self.trigger_time +5: #Stop recording for 10 seconds
                    #print datetime.now().strftime("%b %d, %H:%M:%S"), "Stop recording"
                    self.isRecording = False
                # else:
                #     cv.PutText(curframe,datetime.now().strftime("%b %d, %H:%M:%S"), (25,30),self.font, 0) #Put date on the frame
                #     cv.WriteFrame(self.writer, curframe) #Write the frame
            
            if self.show:
                cv.ShowImage("Image", curframe)
                cv.ShowImage("Res", self.res)
                
            cv.Copy(self.frame2gray, self.frame1gray)
            c=cv.WaitKey(1) % 0x100
            if c==27 or c == 10: #Break if user enters 'Esc'.
                break            

     
    def processImage(self, frame):
        cv.CvtColor(frame, self.frame2gray, cv.CV_RGB2GRAY)
        
        #Absdiff to get the difference between to the frames
        cv.AbsDiff(self.frame1gray, self.frame2gray, self.res)
        
        #Remove the noise and do the threshold
        cv.Smooth(self.res, self.res, cv.CV_BLUR, 5,5)
        cv.MorphologyEx(self.res, self.res, None, None, cv.CV_MOP_OPEN)
        cv.MorphologyEx(self.res, self.res, None, None, cv.CV_MOP_CLOSE)
        cv.Threshold(self.res, self.res, 10, 255, cv.CV_THRESH_BINARY_INV)

    def somethingHasMoved(self):
        nb=0 #Will hold the number of black pixels

        for x in range(self.height): #Iterate the whole image
            for y in range(self.width):
                if self.res[x,y] == 0.0: #If the pixel is black keep it
                    nb += 1
        avg = (nb*100.0)/self.nb_pixels #Calculate the average of black pixel in the image

        if avg > self.threshold:#If over the ceiling trigger the alarm
            return True
        else:
            return False
        
if __name__=="__main__":
    detect = MotionDetectorInstantaneous(doRecord=True)
    detect.run()
