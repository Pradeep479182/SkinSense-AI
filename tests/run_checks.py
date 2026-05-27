import os, sys
from dotenv import load_dotenv
load_dotenv()
try:
    import requests
except Exception as e:
    print('MISSING_REQS: requests not installed')
    sys.exit(3)

k = os.environ.get('ANTHROPIC_API_KEY')
if not k:
    print('KEY=MISSING')
    sys.exit(2)
print('KEY=' + (k[:6] + '...' + k[-6:]))

headers = {'Authorization': f'Bearer {k}'}
try:
    r = requests.get('https://api.anthropic.com/v1/models', headers=headers, timeout=15)
    print('STATUS=' + str(r.status_code))
    if r.status_code == 200:
        try:
            data = r.json()
            if isinstance(data, dict) and 'models' in data:
                print('MODELS_COUNT=' + str(len(data['models'])))
            else:
                print('MODELS_OK')
        except Exception:
            print('MODELS_OK')
    else:
        txt = r.text.replace('\n',' ')[:300]
        print('BODY=' + txt)
except Exception as e:
    print('ERR=' + repr(e))
