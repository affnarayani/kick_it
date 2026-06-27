import random
import time

# Generate a random float between 900 and 1800
delay = random.uniform(900, 1800)

# Sleep for the generated duration
time.sleep(delay)

# Print with flush=True to force the output to the console immediately
print(f"Slept for {delay:.2f} seconds.", flush=True)