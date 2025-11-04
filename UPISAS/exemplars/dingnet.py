from UPISAS.exemplar import Exemplar
import requests
import time

class DingNet(Exemplar):
    def __init__(self, auto_start=False, container_name="dingnet"):
        docker_kwargs = {
            "name": container_name,
            "image": "dingnet",
            "ports": {
                6901: 6901,
                3000: 3000,
            },
            "environment": {
                "VNC_PW": "password",
                "PORT": 3000
            },
            "shm_size": "512m"
        }

        # Initialize parent class first
        super().__init__("http://localhost:3000", docker_kwargs, auto_start)

    def start_run(self):
        # Access _base_url only after parent __init__ has run
        base_url = self.base_endpoint  

        # Wait until DingNet is responsive
        for i in range(30):
            try:
                requests.get(f"{base_url}/monitor_schema", timeout=1)
                break
            except:
                time.sleep(1)

        # Trigger simulation start
        print("Starting DingNet simulation...")
        response = requests.get(f"{base_url}/start_run")
        print("Start run response:", response.text)
        return response
