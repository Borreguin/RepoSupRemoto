import subprocess as sb


def installer():
    sb.run(["pip", "install", "pythonnet"])


if __name__ == "__main__":
    installer()