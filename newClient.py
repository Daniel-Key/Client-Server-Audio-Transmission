import socket
import pyaudio
import wave
import threading
import Queue
import time
import sys
import signal

#Globals
IP_ADDRESS = sys.argv[1]
PORT_NO = int(sys.argv[2])
BUFFER_SIZE = 1024
PARAMETERS = []
PACKET_QUEUE = Queue.Queue()
WINDOW_SIZE = 64
CURRENT_PACKET_SEQUENCE_NUMBER = 0

clientSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def timeout():
    time.sleep(0.01)

def setupStoreAudio():
    file = ""
    if len(sys.argv) == 4:
        file = sys.argv[3]
    else:
        file = "../audio/Test.wav"

    open(file, "a").close()
    global waveFile
    waveFile = wave.open(file, "w")
    waveFile.setnframes(0)
    waveFile.setnchannels(int(PARAMETERS[0]))
    waveFile.setsampwidth(int(PARAMETERS[1]))
    waveFile.setframerate(int(PARAMETERS[2]))

def playAudio(stream, audioArray):
    stream.write(bytes(audioArray))

def streamAudio():
    p = pyaudio.PyAudio()
    stream = p.open(format=p.get_format_from_width(width=int(PARAMETERS[1])), channels=int(PARAMETERS[0]), rate=int(PARAMETERS[2]), output=True)
    audioArray = bytearray()

    playAudioThread = threading.Thread(target = playAudio, args=[stream, audioArray])
    i = 0
    while receivePacketsThread.is_alive() or not PACKET_QUEUE.empty():
        if not PACKET_QUEUE.empty():
            packet = PACKET_QUEUE.get()
            audioArray.extend(packet)
            waveFile.writeframes(packet)
            i = i+1
            if (i%100 == 0):
                print(i)
            if (i > 50 and not playAudioThread.is_alive()):
                if len(sys.argv) == 3:
                    playAudioThread = threading.Thread(target = playAudio, args=[stream, audioArray])
                    playAudioThread.start()
                    audioArray = bytearray()
        elif(i > 50 and not playAudioThread.is_alive()):
            if len(sys.argv) == 3:
                playAudioThread = threading.Thread(target = playAudio, args=[stream, audioArray])
                playAudioThread.start()
                audioArray = bytearray()
    if len(sys.argv) == 3:
        playAudioThread.join()
        if (len(audioArray) > 0):
            stream.write(bytes(audioArray))
        stream.close()

    #Play back stored .wav file
    # waveFile.close()
    # storedWaveFile = wave.open("audio/Test.wav", "rb")
    # stream = p.open(format=p.get_format_from_width(width=int(PARAMETERS[1])), channels=int(PARAMETERS[0]), rate=int(PARAMETERS[2]), output=True)
    # data = storedWaveFile.readframes(BUFFER_SIZE)
    #
    # while len(data) > 0:
    #     stream.write(data)
    #     data = storedWaveFile.readframes(BUFFER_SIZE)
    #
    # stream.stop_stream()
    # stream.close()

    p.terminate()

def receivePackets():
    global CURRENT_PACKET_SEQUENCE_NUMBER
    global WINDOW_SIZE

    print("receivePackets")
    transmitting = True
    restartSequenceNumber = -1

    while transmitting == True:
        data, addr = clientSocket.recvfrom(BUFFER_SIZE)
        if (data[1022:1024] != str(CURRENT_PACKET_SEQUENCE_NUMBER)):
            if restartSequenceNumber == -1:
                clientSocket.sendto(str((CURRENT_PACKET_SEQUENCE_NUMBER-1) % WINDOW_SIZE), (IP_ADDRESS, PORT_NO))
                restartSequenceNumber = CURRENT_PACKET_SEQUENCE_NUMBER

        else:
            if data[1022:1024] == str(restartSequenceNumber):
                restartSequenceNumber = -1
            CURRENT_PACKET_SEQUENCE_NUMBER = (CURRENT_PACKET_SEQUENCE_NUMBER + 1) % WINDOW_SIZE
            time.sleep(0.0005)
            clientSocket.sendto(data[1022:1024], (IP_ADDRESS, PORT_NO))
            PACKET_QUEUE.put(data[:1022])

        if data == "End":
            print "End"
            transmitting = False

def handler(signum, frame):
    raise Exception("Timeout")

data = "00"
while data[:1] != "1":
    clientSocket.sendto("../audio/Beastie_Boys_-_Now_Get_Busy.wav", (IP_ADDRESS, PORT_NO))
    signal.signal(signal.SIGALRM, handler)
    signal.setitimer(0, 0.01)
    try:
        while data[:1] != "1":
            data, addr = clientSocket.recvfrom(BUFFER_SIZE)
            PARAMETERS.append(data[1:])
    except Exception, exc:
        i=0

while data[:1] != "2":
    clientSocket.sendto("ack1", (IP_ADDRESS, PORT_NO))
    signal.signal(signal.SIGALRM, handler)
    signal.setitimer(0, 0.01)
    try:
        while data[:1] != "2":
            data, addr = clientSocket.recvfrom(BUFFER_SIZE)
            PARAMETERS.append(data[1:])
    except Exception, exc:
        i=0

while data[:1] != "3":
    clientSocket.sendto("ack2", (IP_ADDRESS, PORT_NO))
    signal.signal(signal.SIGALRM, handler)
    signal.setitimer(0, 0.01)
    try:
        while data[:1] != "3":
            data, addr = clientSocket.recvfrom(BUFFER_SIZE)
            PARAMETERS.append(data[1:])
    except Exception, exc:
        i=0

#Hacky way to almost guarantee the last acknowledgement being received
done = False
while done == False:
    try:
        time.sleep(0.02)
        for i in range(1, 100):
            clientSocket.sendto("ack3", (IP_ADDRESS, PORT_NO))
        done = True
    except Exception, exc:
        i=0

receivePacketsThread = threading.Thread(target = receivePackets)
receivePacketsThread.start()

while (True):
    if (len(PARAMETERS) == 3):
        break
setupStoreAudio()

streamAudio()
