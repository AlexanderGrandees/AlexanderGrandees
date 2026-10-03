import argparse,secrets
from credential_store_local import CredentialStore
ap=argparse.ArgumentParser();ap.add_argument('--target',required=True);a=ap.parse_args()
s=CredentialStore(); token=s.read(a.target)
if not token:
    token=secrets.token_urlsafe(32);s.write(a.target,token,username='Vexi Browser Pack')
print(token,end='')
