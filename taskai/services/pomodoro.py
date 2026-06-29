from taskai.json_dir_database import JsonDirectoryDatabase
import datetime
import time
from rich import print
from rich.console import Console

def pomodoro_service(
    minutes_on: int,
    minutes_off: int
):
    
    # STATES
    end_time = datetime.datetime.now()

    try:
        
        state = "ready" 
        history = []
        console = Console()
        while True:
            if state == "ready":
                prompt = "Press enter to begin ..."
                input(prompt)
                history.append(f"Starting Pomo for {minutes_on} minutes")
                now = datetime.datetime.now()
                end_time = now + datetime.timedelta(minutes=minutes_on)
                #end_time = now + datetime.timedelta(seconds=5)
                state = "running"
            elif state == "running":
                now = datetime.datetime.now()
                if now < end_time:
                    diff = end_time - now
                    message = f"{diff.seconds // 60}:{str(diff.seconds % 60).zfill(2)} to go"
                    if history[-1].endswith("to go"):
                        history.pop()
                    history.append(message)
                    time.sleep(0.995)
                else:
                    state = "done"
            if state == "done":
                history.append("All Finished! Taking rest now")
                state = "resting"
                end_time = datetime.datetime.now() + datetime.timedelta(minutes=minutes_off)
                #end_time = now + datetime.timedelta(seconds=5)
            if state == "resting":
                now = datetime.datetime.now()
                if now < end_time:
                    diff = end_time - now
                    message = f"{diff.seconds // 60}:{str(diff.seconds % 60).zfill(2)} to go"
                    if history[-1].endswith("to go"):
                        history.pop()
                    history.append(message)
                    time.sleep(0.995)
                else:
                    state = "ready"

            console.clear()
            for val in history:
                console.print(val)
    except KeyboardInterrupt:
        return
            

               
            
