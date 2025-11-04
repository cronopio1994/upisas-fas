from UPISAS.strategy import Strategy

class SignalBasedBaselineStrategy(Strategy):
    MIN_SIGNAL = -48  # dBm
    MAX_SIGNAL = -42  # dBm

    def analyze(self):
        """
        Analyze the latest monitored data to decide if any mote requires adaptation.
        Stores actions in self.knowledge.analysis_data["actions_needed"].
        Returns True if there are adaptations to perform.
        """
        analysis_data = self.knowledge.__dict__.setdefault("analysis_data", {})

        monitored_data = self.knowledge.monitored_data
        if not monitored_data:
            return False

        # Get the latest mote states
        latest_motes = monitored_data.get("moteStates", [])
        if latest_motes and isinstance(latest_motes[0], list):
            latest_motes = latest_motes[0]

        analysis_data["actions_needed"] = []

        for mote in latest_motes:
            signal = mote.get("highestReceivedSignal")
            if signal is None:
                continue

            current_power = mote.get("transmissionPower", 14)
            if signal < self.MIN_SIGNAL:
                new_power = min(current_power + 1, 14)
            elif signal > self.MAX_SIGNAL:
                new_power = max(current_power - 1, 0)
            else:
                continue

            mote_id = mote.get("eui", mote.get("startOffSet"))
            analysis_data["actions_needed"].append((mote_id, new_power))

        return bool(analysis_data["actions_needed"])

    def plan(self):
        analysis_data = self.knowledge.__dict__.setdefault("analysis_data", {})
        actions = analysis_data.get("actions_needed", [])

        if not actions:
            return False

        self.knowledge.plan_data = {"items": []}

        for mote_id, new_power in actions:
            self.knowledge.plan_data["items"].append({
                "id": mote_id,
                "adaptations": [{"name": "transmissionPower", "value": new_power}]
            })

        return True
