import subprocess

def build_project():

    subprocess.run(["cmake", "."])
    subprocess.run(["make"])
