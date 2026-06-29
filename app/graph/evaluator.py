def evaluate_execution(result: str):
    """Evaluate if the execution was successful. """

    if result is None:
        return False 
    
    if not result:
        return False

        if isinstance(result, str):
            if result.atrip == "":
                return False
            
            if "error" in result.lower():
                return False
            
            if "exception" in result.lower():
                return False

            if "traceback" in result.lower():
                return False

    return True