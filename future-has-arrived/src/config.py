import os

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
# Large downloaded models / textures live outside the repo (see setup.sh).
WORK = os.environ.get('FHA_WORK', '/home/user/work')
MODELS = f'{WORK}/models'
ASSETS = f'{WORK}/assets'
BUILD = os.environ.get('FHA_BUILD', f'{WORK}/build')
OUTPUT = f'{PROJECT}/output'

W, H, FPS = 1920, 1080, 30
SR = 48000
