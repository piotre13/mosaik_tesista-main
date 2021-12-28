import socket
import mas.villas_pb2 as villas
import time
import threading
import sys

class Client():


    def __init__(self, local_host, local_port, remote_host, remote_port):
        #self.host = '127.0.0.1'
        #self.port = 12001
        self.rm_host = remote_host # cancel
        self.rm_port = remote_port # cancel
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        local =(local_host, local_port) # listening
        remote = (remote_host, remote_port) #sending
        self.sock.bind(local)
        self.sock.connect(remote)

        self.msg_snd = villas.Message()
        self.sample = self.msg_snd.samples.add()
        self.sample.type = 1
        self.value = self.sample.values.add()

        self.msg_rcv = villas.Message()
        self.rcv_thread = threading.Thread(target=self.receive)
        self.rcv_thread.start() # TODO close the thread because it continue

        print("Listening on " + local_host + ":" + str(local_port))

    def trigger (self, data):
        payload = self.protoB(data)
        self.sock.send(payload)

        #ricezione pacchetto con 12 valori
        #todo preparazione thread per ricezione
        # per ricezione instanziare nuovo messaggio può essere diverso
        #payload, client_address = self.sock.recvfrom(1024)
        #payload = self.msg_rcv.ParseFromString(payload)
        #print(self.msg_rcv.samples[0].values[0].f, client_address)

    def protoB(self, data):
        #sample = self.msg.samples.add()

        self.value.f = data
        self.sample.timestamp.sec = int(time.time())
        self.sample.timestamp.nsec = int(time.process_time_ns())
        #value.f = data # for now must be one double
        return self.msg_snd.SerializeToString()

    def receive (self):
        while self.rcv_thread.is_alive():
            try:
                payload, client_address = self.sock.recvfrom(1024)
                payload = self.msg_rcv.ParseFromString(payload)
                print(self.msg_rcv.samples[0].values[0].f, client_address)
                #for i in range(len(self.msg_rcv.samples[0].values[:])):
                #    self.vars_values_rcv[i] = self.msg_rcv.samples[0].values[i].f
            except Exception:
                print('error in receiving!')

    def stop (self):
        if self.rcv_thread.is_alive():
            try:
                self.rcv_thread._Thread__stop()
            except Exception:
                print(sys.stderr)
        self.sock.close()



if __name__ == '__main__':

    C = Client()
    #C.trigger('Ciao')

    #print(villas_msg)

