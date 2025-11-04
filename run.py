from UPISAS.strategies.signal_baseline import SignalBasedBaselineStrategy
from UPISAS.exemplar import Exemplar
from UPISAS.exemplars.dingnet import DingNet
import signal
import sys
import time
import traceback

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

        while True:
            input("Try to adapt?")
            strategy.monitor(verbose=True)
            if strategy.analyze():
                if strategy.plan():
                    strategy.execute()
            
    except (Exception, KeyboardInterrupt) as e:
        print(str(e))
        traceback.print_exc()
        input("something went wrong")
        exemplar.stop_container()
        sys.exit(0)