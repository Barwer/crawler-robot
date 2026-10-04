import paho.mqtt.client as mqtt
import time
import threading

class controlServo:
    def __init__(self):

        # self.angle = angle
        self.response_payload = None
        self.responses = {}
        self.response_lock = threading.Lock()

        # MQTT broker details
        broker = "192.168.137.1"  # Change if needed
        port = 1883
        self.topic = "servo/angles"
        self.resp_topic = "servo/crawler1_status"

        self.topic2 = "servo2/angles"
        self.resp_topic2 = "servo2/crawler2_status"


        # Create MQTT client with proper API version
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        # Connect and publish
        self.client.connect(broker, port)
        self.client.loop_start()


    def order(self, angles1, angles2):
        # Publish once; Main polls acknowledgements without blocking Tkinter.
        with self.response_lock:
            self.responses.clear()
            self.response_payload = None
        self.client.publish(self.topic, f"{angles1[0][0]},{angles1[0][1]},{angles1[0][2]}")
        self.client.publish(self.topic2, f"{angles2[0][0]},{angles2[0][1]},{angles2[0][2]}")

    def is_complete(self, command_id):
        expected = f"finish,{command_id}"
        with self.response_lock:
            return all(self.responses.get(topic) == expected
                       for topic in (self.resp_topic, self.resp_topic2))

    def close(self):
        self.client.disconnect()
        self.client.loop_stop()

    def on_connect(self, client, userdata, flags, reasonCode, properties=None):
        self.client.subscribe(self.resp_topic)
        self.client.subscribe(self.resp_topic2)

    def on_message(self, client, userdata, msg):
        if msg.topic in (self.resp_topic, self.resp_topic2):
            payload = msg.payload.decode(errors="replace").strip()
            with self.response_lock:
                self.responses[msg.topic] = payload
                self.response_payload = payload

    def get_crawler1_status(self):
        return self.response_payload
