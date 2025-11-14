from UPISAS.strategy import Strategy

# The Signal-Based Adaptation Strategy focuses on regulating the transmission power
# based on the observed Received Signal Strength Indicator (RSSI).

class SignalBasedBaselineStrategy(Strategy):
    """
    Implements the baseline Signal-Based adaptation strategy from the DingNet exemplar.
    
    This strategy adapts the mote's transmission power (Ptx) based on the highest 
    signal strength (RSSI) received by any gateway. It aims to reduce energy 
    consumption (R2) while maintaining reliability (R1).
    """

    MIN_SIGNAL = -48  # dBm: If RSSI is below this, power must increase (signal too weak)
    MAX_SIGNAL = -42  # dBm: If RSSI is above this, power must decrease (signal too strong, waste of energy)
 
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

        for idx, mote in enumerate(latest_motes):
            signal = mote.get("highestReceivedSignal")
            if signal is None:
                continue

            current_power = mote.get("transmissionPower")
            if current_power is None:
                current_power = 7  # default value if missing

            if signal < self.MIN_SIGNAL:
                new_power = min(current_power + 1, 15)  # maxValue from adaptation options
            elif signal > self.MAX_SIGNAL:
                new_power = max(current_power - 1, -1)  # minValue from adaptation options
            else:
                continue

            # Use the index as the ID because ExecuteHandler expects an integer index
            analysis_data["actions_needed"].append((idx, new_power))

        return bool(analysis_data["actions_needed"])

    def plan(self):
        """
        Create the plan_data dictionary for the Execute endpoint.
        """
        analysis_data = self.knowledge.__dict__.setdefault("analysis_data", {})
        actions = analysis_data.get("actions_needed", [])

        if not actions:
            return False

        self.knowledge.plan_data = {"items": []}

        for mote_idx, new_power in actions:
            self.knowledge.plan_data["items"].append({
                "id": mote_idx,
                "adaptations": [{"name": "power", "value": new_power}]
            })

        return True
