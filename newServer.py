import socket
import wave
from playsound import playsound
import time
import threading
import random
import sys
import signal

SERVER_IP_ADDRESS = "138.251.29.159"
SERVER_PORT_NO = int(sys.argv[1])
CLIENT_IP_ADDRESS = ""
CLIENT_PORT_NO = 1
BUFFER_SIZE = 1024
#goBackN variables
WINDOW_SIZE = 32
SEQUENCE_NUMBERS_SIZE = 64
CURRENT_PACKET_SEQUENCE_NUMBER = 0
MOST_RECENT_PACKET_SENT = -1
MOST_RECENT_PACKET_ACKNOWLEDGED = -1
#Stream variables
PACKET_NUMBER = 0
BYTE_NUMBER = 0
REQUEST = False
SERVING = False

serverSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
serverSocket.bind((SERVER_IP_ADDRESS, SERVER_PORT_NO))

def goBackNSend():
    global BYTE_NUMBER
    global PACKET_NUMBER
    global MOST_RECENT_PACKET_SENT
    global MOST_RECENT_PACKET_ACKNOWLEDGED
    global CURRENT_PACKET_SEQUENCE_NUMBER
    timeout = 100

    while (((MOST_RECENT_PACKET_SENT - MOST_RECENT_PACKET_ACKNOWLEDGED) % (SEQUENCE_NUMBERS_SIZE)) == WINDOW_SIZE):
        time.sleep(0.0001)
        if timeout == 0:
            for i in range(WINDOW_SIZE):
                PACKET_NUMBER = PACKET_NUMBER - 1
                BYTE_NUMBER = BYTE_NUMBER - 1022
                CURRENT_PACKET_SEQUENCE_NUMBER = (CURRENT_PACKET_SEQUENCE_NUMBER - (WINDOW_SIZE)) % SEQUENCE_NUMBERS_SIZE
            MOST_RECENT_PACKET_SENT = MOST_RECENT_PACKET_ACKNOWLEDGED
            timeout = 100
        else:
            timeout = timeout - 1

    time.sleep(0.001)
    bytePacket = byteString[BYTE_NUMBER:BYTE_NUMBER+1022]
    bytePacket += str(CURRENT_PACKET_SEQUENCE_NUMBER)
    MOST_RECENT_PACKET_SENT = CURRENT_PACKET_SEQUENCE_NUMBER
    serverSocket.sendto(bytePacket, (CLIENT_IP_ADDRESS, CLIENT_PORT_NO))

    PACKET_NUMBER = PACKET_NUMBER+1
    BYTE_NUMBER = BYTE_NUMBER+1022
    CURRENT_PACKET_SEQUENCE_NUMBER = (CURRENT_PACKET_SEQUENCE_NUMBER + 1) % SEQUENCE_NUMBERS_SIZE

    if (PACKET_NUMBER%100 == 0):
        print PACKET_NUMBER


def goBackNReceive():
    global CURRENT_PACKET_SEQUENCE_NUMBER
    global MOST_RECENT_PACKET_SENT
    global MOST_RECENT_PACKET_ACKNOWLEDGED
    global BYTE_NUMBER
    global PACKET_NUMBER
    ackSize = 2

    errorRecovery = False
    while Serving == True:
        if (errorRecovery == False):
            data, addr = serverSocket.recvfrom(ackSize)
            if int(data) == MOST_RECENT_PACKET_ACKNOWLEDGED:
                errorRecovery = True
            elif int(data) > MOST_RECENT_PACKET_ACKNOWLEDGED or int(data) == ((MOST_RECENT_PACKET_ACKNOWLEDGED + 1) % SEQUENCE_NUMBERS_SIZE):
                MOST_RECENT_PACKET_ACKNOWLEDGED = int(data)

        else:
            if (((MOST_RECENT_PACKET_SENT - MOST_RECENT_PACKET_ACKNOWLEDGED) % (SEQUENCE_NUMBERS_SIZE)) == WINDOW_SIZE):
                time.sleep(0.001)
                for i in range(WINDOW_SIZE):
                    PACKET_NUMBER = PACKET_NUMBER - 1
                    BYTE_NUMBER = BYTE_NUMBER - 1022
                CURRENT_PACKET_SEQUENCE_NUMBER = (MOST_RECENT_PACKET_ACKNOWLEDGED + 1) % SEQUENCE_NUMBERS_SIZE
                errorRecovery = False
                time.sleep(0.01)
                MOST_RECENT_PACKET_SENT = MOST_RECENT_PACKET_ACKNOWLEDGED
    print "Thread exited"

def handler(signum, frame):
    raise Exception("Timeout")

while True:

    while REQUEST == False:
        data, addr = serverSocket.recvfrom(BUFFER_SIZE)
        if data[:8] == "../audio":
            REQUEST = True
            global audioFile
            if len(sys.argv) == 3:
                audioFile = wave.open("../audio/" + sys.argv[2], "r")
            else:
                audioFile = wave.open("../audio/" + data, "r")

            framesNo = audioFile.getnframes()
            byteString = audioFile.readframes(framesNo)
            print len(byteString) / BUFFER_SIZE

            CLIENT_IP_ADDRESS = addr[0]
            CLIENT_PORT_NO = addr[1]

    #Sending stream parameters to the client
    ack = ""
    while ack != "ack1":
        parameter = "1"
        parameter += str(audioFile.getnchannels())
        serverSocket.sendto(parameter, (CLIENT_IP_ADDRESS, CLIENT_PORT_NO))
        signal.signal(signal.SIGALRM, handler)
        signal.setitimer(0, 0.01)
        try:
            while ack != "ack1":
                ack, addr = serverSocket.recvfrom(BUFFER_SIZE)
                print ack
        except Exception, exc:
            i=0

    while ack != "ack2":
        parameter = "2"
        parameter += str(audioFile.getsampwidth())
        serverSocket.sendto(parameter, (CLIENT_IP_ADDRESS, CLIENT_PORT_NO))
        signal.signal(signal.SIGALRM, handler)
        signal.setitimer(0, 0.01)
        try:
            while ack != "ack2":
                ack, addr = serverSocket.recvfrom(BUFFER_SIZE)
                print ack
        except Exception, exc:
            i=0

    while ack != "ack3":
        parameter = "3"
        parameter += str(audioFile.getframerate())
        serverSocket.sendto(parameter, (CLIENT_IP_ADDRESS, CLIENT_PORT_NO))
        signal.signal(signal.SIGALRM, handler)
        signal.setitimer(0, 0.01)
        try:
            while ack != "ack3":
                ack, addr = serverSocket.recvfrom(BUFFER_SIZE)
                print ack
        except Exception, exc:
            i=0

    parametersEnd = "ack3"
    while parametersEnd == "ack3":
        parametersEnd == True
        signal.signal(signal.SIGALRM, handler)
        signal.setitimer(0, 0.01)
        try:
            while True:
                parametersEnd, addr = serverSocket.recvfrom(BUFFER_SIZE)
        except Exception, exc:
            i=0

    #Hacky way to prevent timeout exception
    done = False
    while done == False:
        try:
            time.sleep(0.02)
            done = True
        except Exception, exc:
            i=0

    Serving = True
    goBackNReceiveThread = threading.Thread(target = goBackNReceive)
    goBackNReceiveThread.start()

    while (len(byteString))-BYTE_NUMBER > 1022:
        goBackNSend()

    #Sending last packet
    while (((MOST_RECENT_PACKET_SENT - MOST_RECENT_PACKET_ACKNOWLEDGED) % (SEQUENCE_NUMBERS_SIZE)) == WINDOW_SIZE):
        i = 0
    bytePacket = byteString[BYTE_NUMBER:]
    bytePacket += str(CURRENT_PACKET_SEQUENCE_NUMBER)
    serverSocket.sendto(bytePacket, (CLIENT_IP_ADDRESS, CLIENT_PORT_NO))

    serverSocket.sendto("End", (CLIENT_IP_ADDRESS, CLIENT_PORT_NO))
    Serving = False
    audioFile.close()
    PACKET_NUMBER = 0
    BYTE_NUMBER = 0
    CURRENT_PACKET_SEQUENCE_NUMBER = 0
    MOST_RECENT_PACKET_SENT = -1
    MOST_RECENT_PACKET_ACKNOWLEDGED = -1
    REQUEST = False
