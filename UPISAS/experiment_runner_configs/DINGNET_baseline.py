import random
from EventManager.Models.RunnerEvents import RunnerEvents
from EventManager.EventSubscriptionController import EventSubscriptionController
from ConfigValidator.Config.Models.RunTableModel import RunTableModel
from ConfigValidator.Config.Models.FactorModel import FactorModel
from ConfigValidator.Config.Models.RunnerContext import RunnerContext
from ConfigValidator.Config.Models.OperationType import OperationType
from ExtendedTyping.Typing import SupportsStr
from ProgressManager.Output.OutputProcedure import OutputProcedure as output

from UPISAS.strategies.signal_baseline import SignalBasedBaselineStrategy
from UPISAS.exemplars.dingnet import DingNet

from typing import Dict, List, Optional
from pathlib import Path
from os.path import dirname, realpath
import time
import statistics
MIN_TX_POWER = 1 
MAX_TX_POWER = 14 
MOTE_IDS = [0, 1, 2] # The motes we want to initialize

class RunnerConfig:
    ROOT_DIR = Path(dirname(realpath(__file__)))

    name = "dingnet_baseline_experiment"
    results_output_path = ROOT_DIR / "experiments"
    operation_type = OperationType.AUTO
    time_between_runs_in_ms = 1000

    exemplar = None
    strategy = None
    time_between_adaptation = 5 # Time (seconds) between MAPE-K cycles
    all_snapshots: List[Dict] = [] 
    adaptations_count: int = 0 

    def __init__(self):
        EventSubscriptionController.subscribe_to_multiple_events([
            (RunnerEvents.BEFORE_EXPERIMENT, self.before_experiment),
            (RunnerEvents.BEFORE_RUN, self.before_run),
            (RunnerEvents.START_RUN, self.start_run),
            (RunnerEvents.START_MEASUREMENT, self.start_measurement),
            (RunnerEvents.INTERACT, self.interact),
            (RunnerEvents.STOP_MEASUREMENT, self.stop_measurement),
            (RunnerEvents.STOP_RUN, self.stop_run),
            (RunnerEvents.POPULATE_RUN_DATA, self.populate_run_data),
            (RunnerEvents.AFTER_EXPERIMENT, self.after_experiment),
        ])
        self.run_table_model = None
        output.console_log("DingNet baseline config loaded")

    def create_run_table_model(self) -> RunTableModel:
        # Define factors (what we are changing) and data columns (what we are measuring)
        factor1 = FactorModel("adaptation_mode", ["signal_based_baseline"])
        
        # --- UPDATED DATA COLUMNS ---
        # The key metrics for comparing S1 (Signal-Based) are Reliability and Energy.
        self.run_table_model = RunTableModel(
                    factors=[factor1],
                    repetitions = 3,
                    data_columns=[
                        # R1: Reliability (minimized)
                        "avg_packet_loss",  
                        # R2: Energy Efficiency (minimized)
                        "total_energy_mJ",
                        # Proxy for R2 / Stability
                        "avg_tx_power", 
                        # Overhead (minimized)
                        "adaptations_executed"
                    ],
                )
        return self.run_table_model

    def before_experiment(self):
        output.console_log("Before experiment")

    def before_run(self):
        self.exemplar = DingNet(auto_start=True)       
        output.console_log("Before run")

    def start_run(self, context: RunnerContext):
        adaptation_mode = context.run_variation["adaptation_mode"]

        if context.run_variation["adaptation_mode"] == "signal_based_baseline":
            self.strategy = SignalBasedBaselineStrategy(self.exemplar)
            # Initialize custom knowledge for tracking total adaptations
            setattr(self.strategy.knowledge, "adaptations_executed", 0)
            
        time.sleep(20)
        self.exemplar.start_run()
        time.sleep(5)

        initial_adaptation_items = []
        for mote_id in MOTE_IDS:
            # Generate a random power value between 1 and 14 (inclusive)
            random_power = random.randint(MIN_TX_POWER, MAX_TX_POWER)
            
            initial_adaptation_items.append({
                "id": mote_id, 
                "adaptations": [
                    {"name": "power", "value": random_power},
                ]})
            output.console_log(f"Mote {mote_id} initialized with power: {random_power} dBm")

    
        initial_adaptation_data = {"items": initial_adaptation_items}
        
        self.strategy.execute(adaptation=initial_adaptation_data)
        
        time.sleep(30)
        output.console_log("Start run")

    def start_measurement(self, context: RunnerContext):
        output.console_log("Start measurement")

    def interact(self, context: RunnerContext):
        """The main MAPE-K loop runs here for the duration of the experiment."""
    
        for _ in range(3):
            # 1. Monitor
            self.strategy.monitor(verbose=False)
            
            # Append the latest monitored data to our list for later analysis
            last_monitored = getattr(self.strategy.knowledge, "monitored_data", None)
            if last_monitored:
                if isinstance(last_monitored, list) and last_monitored:
                    self.all_snapshots.append(last_monitored[-1])
                elif isinstance(last_monitored, dict):
                     self.all_snapshots.append(last_monitored)


            # 2. Analyze, Plan, Execute
            if self.strategy.analyze():
                if self.strategy.plan():
                    self.strategy.execute()
                    # 3. Track total adaptations executed
                    self.adaptations_count += len(self.strategy.knowledge.plan_data.get("items", []))


            # 4. Wait for the next interval
            time.sleep(self.time_between_adaptation)

        output.console_log("Config.interact() called!")

    def stop_measurement(self, context: RunnerContext):
        output.console_log("Stop measurement")

    def stop_run(self, context: RunnerContext):
        self.exemplar.stop_container()
        output.console_log("Stop run")

    def populate_run_data(self, context: RunnerContext) -> Optional[Dict[str, SupportsStr]]:
        """Calculate and return the final aggregate metrics for the run."""
        output.console_log("Config.populate_run_data() called! Aggregating data...")
        
        all_packet_losses, all_tx_powers = [], []
        total_energy_consumption_mJ = 0.0

        if not self.all_snapshots:
            output.console_log("No snapshots recorded for this run.")
            return None

        # --- Aggregation Logic (Unchanged, calculates raw values) ---
        for snapshot in self.all_snapshots:
            mote_states = snapshot.get("moteStates", [])
            if mote_states and isinstance(mote_states[0], list):
                mote_states = mote_states[0]
            
            for mote in mote_states:
                # Extract metrics
                tx = mote.get("transmissionPower")
                packet_loss = mote.get("packetLoss")
                
                if packet_loss is not None:
                    # PacketLoss is typically a fraction (0.0 to 1.0)
                    all_packet_losses.append(float(packet_loss))
                
                if tx is not None:
                    tx_power_dbm = float(tx)
                    all_tx_powers.append(tx_power_dbm)
                    
                    # Energy calculation: P(mW) = 10^(P(dBm)/10), E(mJ) = P(mW) * Time(s)
                    tx_power_mW = 10 ** (tx_power_dbm / 10.0)
                    total_energy_consumption_mJ += tx_power_mW * self.time_between_adaptation

        # Calculate final averages
        # Use simple mean of fractions for overall packet loss
        avg_packet_loss = statistics.mean(all_packet_losses) if all_packet_losses else 0.0
        avg_tx_power = statistics.mean(all_tx_powers) if all_tx_powers else 0.0
        total_adaptations = self.adaptations_count
        output.console_log(
            f"Results: PL={avg_packet_loss:.4f}, Energy={total_energy_consumption_mJ:.2f} mJ, TxP={avg_tx_power:.2f}, Adapts={total_adaptations}"
        )

        # --- UPDATED: Return keys match the RunTableModel columns ---
        return {
            "avg_packet_loss": avg_packet_loss,
            "total_energy_mJ": total_energy_consumption_mJ,
            "avg_tx_power": avg_tx_power,
            "adaptations_executed": total_adaptations
        }
        # -----------------------------------------------------------

   
    def after_experiment(self):
        self.exemplar.stop_container()
        output.console_log("After experiment")
