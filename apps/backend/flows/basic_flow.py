from prefect import flow, task
import time

@task
def process_data(data: str):
    print(f"Processing data: {data}")
    time.sleep(1)
    return f"Processed {data}"

@flow(name="Basic Agent Flow")
def agent_flow(input_data: str = "default"):
    result = process_data(input_data)
    print(f"Flow result: {result}")
    return result

if __name__ == "__main__":
    agent_flow(input_data="test run")
