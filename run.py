from UPISAS.strategies.signal_baseline import SignalBasedBaselineStrategy
from UPISAS.exemplar import Exemplar
from UPISAS.exemplars.dingnet import DingNet
import signal
import sys
import time
import traceback

# Your manual adaptation payload
pre_adaptation = {
    "items": [
        {"id": 0, "adaptations": [{"name": "power", "value": 12}]},
        {"id": 1, "adaptations": [{"name": "power", "value": 10}]},
        {"id": 2, "adaptations": [{"name": "power", "value": 1}]}
    ]
}

def get_latest_motes(strategy):
    motes_history = strategy.knowledge.monitored_data.get("moteStates", [])
    if not motes_history:
        return []

    latest = motes_history[-1]

    # Sometimes DingNet nests lists like [[{...}, {...}]]
    if isinstance(latest, list) and len(latest) > 0 and isinstance(latest[0], list):
        latest = latest[0]

    return latest
# ---- end helper ----

if __name__ == '__main__':
    
    exemplar = DingNet(auto_start=True)
    time.sleep(3)
    exemplar.start_run()
    time.sleep(3)

    try:
        strategy = SignalBasedBaselineStrategy(exemplar)

        strategy.get_monitor_schema()
        strategy.get_adaptation_options_schema()
        strategy.get_execute_schema()

        # Execute the manual adaptation
        strategy.execute(pre_adaptation)
        print("Manual adaptation posted, waiting 5s...")
        time.sleep(5)

        # Monitor after manual adaptation
        strategy.monitor(verbose=False)
        print("AFTER manual adaptation:", get_latest_motes(strategy))

        while True:
            input("Try to adapt?")

            strategy.monitor(verbose=False) 
             # Show monitored state BEFORE decision
            print("BEFORE:", get_latest_motes(strategy))
            if strategy.analyze():
                if strategy.plan():
                    strategy.execute()
                    # Wait a bit to allow the system to apply and send new packets
                    time.sleep(5)

                    # Monitor again to observe any change
                    strategy.monitor(verbose=False)
                    print("AFTER:", get_latest_motes(strategy))
    except (Exception, KeyboardInterrupt) as e:
        print(str(e))
        traceback.print_exc()
        input("something went wrong")
        exemplar.stop_container()
        sys.exit(0)