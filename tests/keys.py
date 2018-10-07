import json

with open('ios_deploy.json', 'r') as fh:
    d = json.load(fh)

def recursive_items(dictionary):
    for key, value in dictionary.items():
        if type(value) is dict:
            yield from recursive_items(value)
        else:
            yield (key, value)

keys_u = set()
for key, value in recursive_items(d):
    keys_u.add(key)
    print("\t"+str(key))
#print(keys_u)
