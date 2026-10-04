import paho.mqtt.client as mqtt
import time
import threading

class controlServo:
    def __init__(self):

        # self.angle = angle
        self.response_payload = None
        self.responses = {}
        self.response_lock = threading.Lock()
        self.broker_connected = False
        self.last_seen = {}
        self.last_payloads = {}
        self.pending_command = None
        self.active_response_topics = ()
        self.timed_out_topics = set()

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
        self.client.on_disconnect = self.on_disconnect

        # Connect and publish
        self.client.connect(broker, port)
        self.client.loop_start()


    def order(self, angles1=None, angles2=None):
        # Publish once; Main polls acknowledgements without blocking Tkinter.
        if not self.client.is_connected():
            raise RuntimeError("MQTT broker is not connected. Wait for Broker: connected before Run.")
        if angles1 is None and angles2 is None:
            raise ValueError("At least one robot command is required")
        with self.response_lock:
            self.responses.clear()
            self.response_payload = None
            self.active_response_topics = tuple(topic for topic, angles in
                ((self.resp_topic, angles1), (self.resp_topic2, angles2)) if angles is not None)
            self.pending_command = (angles1 if angles1 is not None else angles2)[0][2]
            self.timed_out_topics = set()
        if angles1 is not None:
            payload1 = f"{angles1[0][0]},{angles1[0][1]},{angles1[0][2]}"
            print(f"[MQTT SEND] {self.topic}: {payload1}")
            self._publish_command(self.topic, payload1)
        if angles2 is not None:
            payload2 = f"{angles2[0][0]},{angles2[0][1]},{angles2[0][2]}"
            print(f"[MQTT SEND] {self.topic2}: {payload2}")
            self._publish_command(self.topic2, payload2)

    def _publish_command(self, topic, payload):
        result = self.client.publish(topic, payload, retain=False)
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError(f"MQTT publish failed for {topic}: {mqtt.error_string(result.rc)}")
        print(f"[MQTT QUEUED] {topic} (mid={result.mid}); waiting for robot finish")

    def is_complete(self, command_id):
        with self.response_lock:
            return all(self._matches(self.responses.get(topic), command_id)
                       for topic in self.active_response_topics)

    @staticmethod
    def _matches(payload, command_id):
        if not payload:
            return False
        parts = [part.strip() for part in payload.split(',')]
        return len(parts) == 2 and parts[0] == 'finish' and parts[1] == str(command_id)

    def acknowledgement_details(self, command_id):
        with self.response_lock:
            responses = dict(self.responses)
        lines = [f"Expected: finish,{command_id}"]
        for robot, topic in ((1, self.resp_topic), (2, self.resp_topic2)):
            if topic not in self.active_response_topics:
                continue
            payload = responses.get(topic)
            status = 'OK' if self._matches(payload, command_id) else 'WAITING / WRONG ID'
            lines.append(f"Robot {robot} [{status}] {topic}: {payload!r}")
        return '\n'.join(lines)

    def close(self):
        self.client.disconnect()
        self.client.loop_stop()

    def mark_timeout(self, command_id):
        with self.response_lock:
            self.timed_out_topics = {topic for topic in self.active_response_topics
                                    if not self._matches(self.responses.get(topic), command_id)}

    def connection_snapshot(self, recent_seconds=30.0):
        """Report observed replies, not unverified ESP8266 online presence."""
        now = time.monotonic()
        with self.response_lock:
            robots = []
            for robot_id, topic in ((1, self.resp_topic), (2, self.resp_topic2)):
                seen = self.last_seen.get(topic)
                age = None if seen is None else max(0.0, now - seen)
                if not self.broker_connected:
                    state = 'broker_offline'
                elif topic in self.timed_out_topics:
                    state = 'timeout'
                elif topic in self.active_response_topics and not self._matches(
                        self.responses.get(topic), self.pending_command):
                    state = 'waiting'
                elif age is None:
                    state = 'unknown'
                elif age <= recent_seconds:
                    state = 'recent'
                else:
                    state = 'stale'
                robots.append({'id': robot_id, 'state': state, 'age': age,
                               'payload': self.last_payloads.get(topic), 'topic': topic})
            return {'broker_connected': self.broker_connected, 'robots': robots}

    def on_connect(self, client, userdata, flags, reasonCode, properties=None):
        print(f"[MQTT CONNECT] {reasonCode}")
        with self.response_lock:
            self.broker_connected = reasonCode == 0
            self.last_seen.clear()
            self.last_payloads.clear()
        if reasonCode != 0:
            return
        self.client.subscribe(self.resp_topic)
        self.client.subscribe(self.resp_topic2)

    def on_disconnect(self, client, userdata, disconnect_flags, reasonCode, properties=None):
        with self.response_lock:
            self.broker_connected = False
        print(f"[MQTT DISCONNECT] {reasonCode}")

    def on_message(self, client, userdata, msg):
        if msg.topic in (self.resp_topic, self.resp_topic2):
            payload = msg.payload.decode(errors="replace").strip()
            print(f"[MQTT RECEIVE] {msg.topic}: {payload}")
            # Retained status is historical, not evidence of a live robot.
            if msg.retain:
                return
            with self.response_lock:
                self.responses[msg.topic] = payload
                self.response_payload = payload
                self.last_seen[msg.topic] = time.monotonic()
                self.last_payloads[msg.topic] = payload

    def get_crawler1_status(self):
        return self.response_payload
