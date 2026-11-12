"""Provision only the disposable localhost server used by sonar-demo.yml."""
import base64
import http.client
import json
import os
from pathlib import Path
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

URL = 'http://localhost:9000'
PROJECT = 'cicd-demo'
GATE = 'Demo - no reliability bugs'


def request(endpoint, parameters=None, auth=None):
    data = urllib.parse.urlencode(parameters).encode() if parameters is not None else None
    req = urllib.request.Request(URL + '/api/' + endpoint, data=data)
    if auth:
        req.add_header('Authorization', auth)
    with urllib.request.urlopen(req, timeout=15) as response:
        body = response.read()
        return json.loads(body) if body else {}


def basic(password):
    return 'Basic ' + base64.b64encode(('admin:' + password).encode()).decode()


def setup():
    for _ in range(90):
        try:
            if request('system/status').get('status') == 'UP':
                break
        except (urllib.error.URLError, TimeoutError, ConnectionError, http.client.HTTPException):
            pass
        time.sleep(2)
    else:
        raise RuntimeError('SonarQube did not become ready')
    password = secrets.token_urlsafe(32)
    print('::add-mask::' + password, flush=True)
    request('users/change_password', {'login': 'admin', 'previousPassword': 'admin',
                                     'password': password}, basic('admin'))
    auth = basic(password)
    request('projects/create', {'project': PROJECT, 'name': 'CI/CD Bug Demonstration'}, auth)
    # Pin the rule under demonstration: built-in profiles change across releases.
    request('qualityprofiles/create', {'language': 'java',
            'name': 'Demo Java null safety'}, auth)
    profiles = request('qualityprofiles/search?language=java', auth=auth)['profiles']
    profile = next(p for p in profiles if p['name'] == 'Demo Java null safety')
    request('qualityprofiles/activate_rule', {'key': profile['key'],
            'rule': 'java:S2259'}, auth)
    request('qualityprofiles/add_project', {'language': 'java',
            'qualityProfile': profile['name'], 'project': PROJECT}, auth)
    request('qualitygates/create', {'name': GATE}, auth)
    request('qualitygates/create_condition', {'gateName': GATE,
            'metric': 'software_quality_reliability_rating', 'op': 'GT', 'error': '1'}, auth)
    request('qualitygates/select', {'gateName': GATE, 'projectKey': PROJECT}, auth)
    token = request('user_tokens/generate', {'name': 'disposable-ci-analysis'}, auth)['token']
    print('::add-mask::' + token, flush=True)
    with open(os.environ['GITHUB_ENV'], 'a') as output:
        output.write('SONAR_TOKEN=' + token + '\n')
    print('Assigned gate: overall reliability rating must be A.')


def evidence():
    if not os.environ.get('SONAR_TOKEN'):
        print('Server setup failed; no analysis evidence is available.')
        return
    auth = 'Bearer ' + os.environ['SONAR_TOKEN']
    output = Path('sonar-evidence')
    output.mkdir(exist_ok=True)
    gate = request('qualitygates/project_status?projectKey=' + PROJECT, auth=auth)
    issues = request('issues/search?componentKeys=' + PROJECT + '&resolved=false&ps=100', auth=auth)
    (output / 'quality-gate.json').write_text(json.dumps(gate, indent=2))
    (output / 'issues.json').write_text(json.dumps(issues, indent=2))
    status = gate['projectStatus']['status']
    lines = ['## SonarQube demonstration', '', 'Quality gate: **' + status + '**', '',
             'Commit: `' + os.environ.get('GITHUB_SHA', 'local') + '`', '',
             'This is a disposable server. Production deployment is not run.', '',
             '| Rule | File | Line | Message |', '|---|---|---|---|']
    for issue in issues.get('issues', []):
        values = [issue['rule'], issue['component'], str(issue.get('line', '')),
                  issue['message'].replace('|', '/')]
        lines.append('| ' + ' | '.join(values) + ' |')
    report = '\n'.join(lines) + '\n'
    (output / 'summary.md').write_text(report)
    with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as summary:
        summary.write(report)
    print(report)


if __name__ == '__main__':
    if sys.argv[1:] == ['setup']:
        setup()
    elif sys.argv[1:] == ['evidence']:
        evidence()
    else:
        raise SystemExit('Usage: sonar-demo.py setup|evidence')
