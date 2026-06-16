import psutil

def get_system_resources():
    return {
        "cpu_percent" : psutil.cpu_percent(interval=1) ,
        "ram_available_gb":
            round(
                psutil.virtual_memory().available /
                (1024**3), 2
            )
    }

print(get_system_resources()) 