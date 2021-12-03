import paramiko

class MQTT_Device:
    mqtt_id = str
    mosq_user = str
    mosq_pass = str
    ssh = paramiko.SSHClient

    def __init__(self, i, u, p):
        self.mqtt_id = i
        self.mosq_user = u
        self.mosq_pass = p

    def set_ssh_handle(self, h):
        self.ssh = h

    def status(self) -> str:
        try:
            transport = self.ssh.get_transport()
            channel1 = transport.open_session()
            channel2 = transport.open_session()

            channel1.exec_command("mosquitto_sub -u " + self.mosq_user + " -P " + self.mosq_pass + " -t 'stat/" + self.mqtt_id + "' -C 1")
            channel2.exec_command("mosquitto_pub -u " + self.mosq_user + " -P " + self.mosq_pass + " -t 'cmnd/" + self.mqtt_id + "' -m '' > /dev/null")

            res = channel1.recv(20).decode('utf-8')
        except Exception as e:
            res = str(e)

        return res

    def set_on(self) -> str:
        res = ""

        try:
            self.ssh.exec_command("mosquitto_pub -u " + self.mosq_user + " -P " + self.mosq_pass + " -t 'cmnd/" + self.mqtt_id + "' -m '1' > /dev/null")
        except Exception as e:
            res = str(e)

        return res

    def set_off(self) -> str:
        res = ""

        try:
            self.ssh.exec_command("mosquitto_pub -u " + self.mosq_user + " -P " + self.mosq_pass + " -t 'cmnd/" + self.mqtt_id + "' -m '0' > /dev/null")
        except Exception as e:
            res = str(e)

        return res
