# FE8R Wiki

This is the github repo for <a href="https://fe8r-guide.onrender.com/">FE8R Wiki</a>.

## About The Project

<a href="https://fe8r-guide.onrender.com/">FE8R Wiki</a> is an online reference guide for <a href="https://github.com/FE8Dev/FE8RProject">Fire Emblem 8R</a>, an (awesome) remake using the <a href="https://lex-talionis.net/">Lex Talionis</a> engine.

## Getting Started

### Prerequisites

Python >=3.10

### Installation

1. Clone this repo

    ```bash
    git clone --depth 1 https://github.com/rygon1/fe8r-guide.git
    ```

2. Run deploy.sh

    ```bash
    cd fe8r-guide
    chmod +x deploy.sh
    ./deploy.sh
    ```

The next ones are optional, just in case this repo is out of date with the FE8RProject files.

1. Clone the FE8R git repo

    ```bash
    git clone --depth 1 https://github.com/FE8Dev/FE8RProject/tree/main/FE8R.ltproj
    ```

2. Open ltprojpath.txt inside the fe8r-guide directory. Paste your directory path to FE8R.ltproj
3. In the fe8r-guide directory, run get_resources.py
  
    ```bash
    python get_resources.py
    ```

### Running the server locally

```bash
source .venv/bin/activate
gunicorn wsgi:app
```

Go to http://127.0.0.1:8000 in your internet browser of choice.

If you're on Windows and not using WSL, try using Waitress instead of Gunicorn.
