from app.editing.validator import validate_python

good = """
def add(a,b):
    return a+b
"""

bad = """
def add(a,b)
    return a+b
"""

print(validate_python(good))

print(validate_python(bad))